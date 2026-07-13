"""Deterministic policy engine.

This module is intentionally LLM-free: given detected entities and intake
constraints it produces findings and a verdict that are reproducible and
auditable. Brand matching is type-aware (a PERSON named "Worthing" never
trips a brand rule) and alias-normalized ("DUNKIN' DOUGHNUTS" matches a
"Dunkin' Donuts" restriction).
"""

from __future__ import annotations

import re
import unicodedata

from .schemas import (
    DetectedEntity,
    EntityType,
    Finding,
    FindingCategory,
    HITLStatus,
    IntakeConstraints,
    ScriptAnalysis,
    Severity,
    SourceApi,
    StageFailure,
    Verdict,
    VFXSlate,
)

# ---------------------------------------------------------------------------
# Normalization & aliases
# ---------------------------------------------------------------------------
_ALIASES: dict[str, str] = {
    "dunkin doughnuts": "dunkin donuts",
    "dunkin": "dunkin donuts",
    "coca cola": "coca-cola",
    "coke": "coca-cola",
    "lv": "louis vuitton",
    "vuse alto": "vuse",
    "vuse go": "vuse",
    "facebook inc": "facebook",
    "meta": "facebook",
}

# Brands whose on-screen presence is a Standards & Practices issue in itself,
# independent of sponsor exclusivity. Extensible via IntakeConstraints.custom_rules
# review; kept table-driven so legal can audit the exact rule set.
SUBSTANCE_CATEGORIES: dict[str, str] = {
    "vuse": "TOBACCO_VAPE",
    "juul": "TOBACCO_VAPE",
    "winston": "TOBACCO",
    "marlboro": "TOBACCO",
    "camel": "TOBACCO",
    "heineken": "ALCOHOL",
    "budweiser": "ALCOHOL",
    "smirnoff": "ALCOHOL",
}

# Ratings at which each substance category is disallowed on screen as
# recognizable branding. Broadcast tobacco advertising is prohibited outright.
_RATING_BLOCKLIST: dict[str, set[str]] = {
    "TV-Y": {"TOBACCO", "TOBACCO_VAPE", "ALCOHOL"},
    "TV-Y7": {"TOBACCO", "TOBACCO_VAPE", "ALCOHOL"},
    "TV-G": {"TOBACCO", "TOBACCO_VAPE", "ALCOHOL"},
    "TV-PG": {"TOBACCO", "TOBACCO_VAPE", "ALCOHOL"},
    "TV-14": {"TOBACCO", "TOBACCO_VAPE"},
    "TV-MA": {"TOBACCO", "TOBACCO_VAPE"},
    "PG": {"TOBACCO", "TOBACCO_VAPE", "ALCOHOL"},
    "PG-13": {"TOBACCO", "TOBACCO_VAPE"},
    "R": set(),
}


def normalize_name(name: str) -> str:
    """Casefold, strip accents/punctuation/possessives, collapse whitespace, apply aliases."""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.casefold().replace("’", "'")
    s = re.sub(r"'s\b", "", s)          # possessives: "victoria's" -> "victoria"
    s = re.sub(r"[^a-z0-9 ]+", " ", s)  # punctuation -> space
    s = re.sub(r"\s+", " ", s).strip()
    return _ALIASES.get(s, s)


def _name_matches(entity_name: str, rule_name: str) -> bool:
    """Whole-phrase match after normalization ("Sony audio headset" matches "Sony")."""
    e, r = normalize_name(entity_name), normalize_name(rule_name)
    if not e or not r:
        return False
    if e == r:
        return True
    return re.search(rf"\b{re.escape(r)}\b", e) is not None


def scan_text_for_terms(text: str, terms: list[str]) -> list[str]:
    """Deterministic whole-word scan of raw text (e.g. OCR output) for rule terms."""
    hits = []
    for term in terms:
        pattern = re.escape(term).replace(r"\ ", r"\s+")
        if re.search(rf"\b{pattern}\b", text, re.IGNORECASE):
            hits.append(term)
    return hits


def normalize_text_block(text: str) -> str:
    """normalize_name semantics applied to a whole document (no alias lookup)."""
    s = unicodedata.normalize("NFKD", text)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.casefold().replace("’", "'")
    s = re.sub(r"'s\b", "", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s)


def _term_variants(term: str) -> set[str]:
    """A rule term plus every alias that normalizes to the same canonical name."""
    canonical = normalize_name(term)
    return {canonical} | {alias for alias, canon in _ALIASES.items() if canon == canonical}


def _overlaps_person(name: str, person_norms: set[str]) -> bool:
    n = normalize_name(name)
    return any(_name_matches(p, n) or _name_matches(n, p) for p in person_norms)


# Titles that mark the following capitalized word as a character name, not a
# brand ('Lady Bracknell'). Kept short and unambiguous on purpose: a term like
# 'Dr Pepper' is a full multi-word brand and never matches this pattern.
_HONORIFICS = (
    "Lady|Lord|Sir|Dame|Miss|Mrs|Mr|Ms|Dr|Rev|Reverend|Captain|Colonel|"
    "Professor|Aunt|Uncle|Cousin|Madam|Madame"
)

# Screenplay/theatrical structure the NL API misclassifies as ORGANIZATION
# (observed live: 'ACT III', 'FIRST ACT', 'Enter Lane'). Headings must be
# structure words optionally followed by numerals only, so real org names
# like 'Scene Systems Inc' never match.
_STRUCTURE_HEADING = re.compile(
    r"^(?:(?:first|second|third|fourth|fifth|final)\s+)?"
    r"(?:act|scene|prologue|epilogue|intermission|interlude)"
    r"(?:\s+[\divxlc]+)?\.?$",
    re.IGNORECASE,
)
_STAGE_DIRECTION = re.compile(r"^(?:enter|exit|exeunt|re-?enter)\b", re.IGNORECASE)


def is_screenplay_structure_term(name: str) -> bool:
    """True for stage headings/directions ('ACT III', 'Enter Lane') that are
    document structure, not organizations."""
    stripped = name.strip()
    return bool(_STRUCTURE_HEADING.match(stripped) or _STAGE_DIRECTION.match(stripped))


def scan_script_for_rule_entities(
    raw_text: str,
    constraints: IntakeConstraints,
    existing_entities: list[DetectedEntity],
) -> list[DetectedEntity]:
    """Deterministic scan of script text for the deal's OWN terms.

    NER misses brands in all-caps action lines ('DUNKIN' DOUGHNUTS coffee') and
    lowercase prop notes ('an apple device prop'). Unlike the legacy hardcoded
    world-brand list, this scans ONLY terms the operator supplied (restricted
    competitors + primary sponsor) plus the substance table — so it cannot
    invent findings about brands nobody asked about.

    Suppression rules keep precision:
    - a term already detected by NER is not duplicated;
    - a term whose name overlaps a detected PERSON is skipped (the 'Worthing
      as competitor' trap — in this document that name is a character);
    - a term that appears in the text behind an honorific ('Lady Bracknell',
      'Mr. Worthing') is a character name even when NER failed to type it as
      PERSON (observed live: NL never returned Lady Bracknell as a person);
      the honorific name is emitted as a PERSON entity so downstream
      person-overlap suppression sees it too;
    - substance brands (which collide with common words/names: camel, winston)
      additionally require a capitalized occurrence in the raw text.
    """
    person_norms = {normalize_name(e.name) for e in existing_entities if e.entity_type == EntityType.PERSON}
    existing_brand_norms = {
        normalize_name(e.name) for e in existing_entities if e.entity_type in _BRANDLIKE
    }
    norm_text = normalize_text_block(raw_text)
    found: list[DetectedEntity] = []

    deal = constraints.exclusivity_deals
    deal_terms = list(deal.restricted_competitors)
    if deal.primary_sponsor:
        deal_terms.append(deal.primary_sponsor)

    # Honorific pass: a deal term used as '<honorific> <Term>' in the text is a
    # character name in this document, not a brand.
    for term in deal_terms:
        match = re.search(
            rf"\b({_HONORIFICS})\.?\s+({re.escape(term)})\b", raw_text, re.IGNORECASE
        )
        if match and normalize_name(match.group(0)) not in person_norms:
            honorific_name = f"{match.group(1).title()} {match.group(2).title()}"
            person_norms.add(normalize_name(honorific_name))
            found.append(
                DetectedEntity(
                    name=honorific_name,
                    entity_type=EntityType.PERSON,
                    source_api=SourceApi.DETERMINISTIC_TEXT_SCAN,
                    detail="Deal term appears behind an honorific; treated as a character name",
                )
            )

    def _emit(term: str, detail: str) -> None:
        if normalize_name(term) in existing_brand_norms:
            return
        if _overlaps_person(term, person_norms):
            return
        found.append(
            DetectedEntity(
                name=term,
                entity_type=EntityType.ORGANIZATION,
                source_api=SourceApi.DETERMINISTIC_TEXT_SCAN,
                detail=detail,
            )
        )
        existing_brand_norms.add(normalize_name(term))

    for term in deal_terms:
        if any(re.search(rf"\b{re.escape(v)}\b", norm_text) for v in _term_variants(term)):
            _emit(term, "Exclusivity-deal term found in script text (NER-independent scan)")

    for brand in SUBSTANCE_CATEGORIES:
        capitalized = re.search(rf"\b({brand.title()}|{brand.upper()})\b", raw_text)
        if capitalized:
            _emit(brand.title(), "Substance-category brand found capitalized in script text")

    return found


def substance_category(entity_name: str) -> str | None:
    n = normalize_name(entity_name)
    for brand, category in SUBSTANCE_CATEGORIES.items():
        if _name_matches(n, brand):
            return category
    return None


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
_BRANDLIKE = (EntityType.BRAND, EntityType.ORGANIZATION)


def _slates_for(entity: DetectedEntity) -> list[VFXSlate]:
    return [
        VFXSlate(
            start_timecode=tc.start,
            end_timecode=tc.end,
            target_description=f"Mask '{entity.name}' branding",
        )
        for tc in entity.timecodes
    ]


def evaluate_entities(
    entities: list[DetectedEntity],
    constraints: IntakeConstraints,
    script_analysis: ScriptAnalysis | None = None,
) -> list[Finding]:
    """Apply exclusivity, S&P and clearance rules to detected entities."""
    findings: list[Finding] = []
    deal = constraints.exclusivity_deals
    person_assessments = {
        normalize_name(p.name): p for p in (script_analysis.persons if script_analysis else [])
    }
    person_norms = {normalize_name(e.name) for e in entities if e.entity_type == EntityType.PERSON}

    for ent in entities:
        if ent.entity_type in _BRANDLIKE:
            # NER misclassification guard: if this 'organization' shares its
            # name with a detected PERSON in the same document (e.g. NL tagging
            # 'Manservant Lady Bracknell Hon' as ORGANIZATION), brand rules do
            # not apply — within one script a name is one entity. This applies
            # to text-scan entities too (defense in depth; the scan also
            # suppresses at emit time).
            if _overlaps_person(ent.name, person_norms):
                continue
            # Screenplay structure ('ACT III', 'Enter Lane') misclassified as
            # ORGANIZATION by NER is document layout, not a brand. Text-scan
            # entities are exempt: those are the operator's own deal terms.
            if ent.source_api != SourceApi.DETERMINISTIC_TEXT_SCAN and is_screenplay_structure_term(
                ent.name
            ):
                continue
            findings.extend(_evaluate_brandlike(ent, constraints))
        elif ent.entity_type == EntityType.PERSON:
            findings.extend(_evaluate_person(ent, person_assessments))
        # LOCATION / OTHER entities are recorded on the report but raise no findings.

    # Restricted-competitor rules that matched nothing get no finding — the
    # absence is visible in the report via detected_entities, never invented.
    _ = deal
    return findings


def _evaluate_brandlike(ent: DetectedEntity, constraints: IntakeConstraints) -> list[Finding]:
    deal = constraints.exclusivity_deals
    out: list[Finding] = []

    category = substance_category(ent.name)
    blocked_categories = _RATING_BLOCKLIST.get(constraints.target_rating.upper(), {"TOBACCO", "TOBACCO_VAPE"})
    if category and category in blocked_categories:
        out.append(
            Finding(
                category=FindingCategory.SP_SUBSTANCE_VIOLATION,
                severity=Severity.CRITICAL,
                entity=ent.name,
                entity_type=ent.entity_type,
                description=(
                    f"'{ent.name}' is recognizable {category} branding; disallowed under "
                    f"target rating {constraints.target_rating} Standards & Practices."
                ),
                remediation="Remove the prop/branding from set, or apply the attached VFX paint-out slate.",
                source_api=ent.source_api,
                confidence=ent.confidence,
                timecodes=ent.timecodes,
                vfx_slates=_slates_for(ent),
                requires_human_review=True,
            )
        )
        return out  # substance violation dominates; no double-flag as uncleared brand

    if any(_name_matches(ent.name, r) for r in deal.restricted_competitors):
        out.append(
            Finding(
                category=FindingCategory.SPONSOR_EXCLUSIVITY_BREACH,
                severity=Severity.CRITICAL,
                entity=ent.name,
                entity_type=ent.entity_type,
                description=(
                    f"'{ent.name}' matches a restricted competitor under the active "
                    f"exclusivity deal (primary sponsor: {deal.primary_sponsor or 'n/a'})."
                ),
                remediation=(
                    "Rewrite the reference / substitute the prop, or execute the attached "
                    "VFX slate. Requires sign-off before distribution."
                ),
                source_api=ent.source_api,
                confidence=ent.confidence,
                timecodes=ent.timecodes,
                vfx_slates=_slates_for(ent),
                requires_human_review=True,
            )
        )
        return out

    if deal.primary_sponsor and _name_matches(ent.name, deal.primary_sponsor):
        out.append(
            Finding(
                category=FindingCategory.SPONSOR_VERIFIED,
                severity=Severity.INFO,
                entity=ent.name,
                entity_type=ent.entity_type,
                description=f"'{ent.name}' matches the primary sponsor; presence is contractually cleared.",
                remediation="None required.",
                source_api=ent.source_api,
                confidence=ent.confidence,
                timecodes=ent.timecodes,
            )
        )
        return out

    cat = (
        FindingCategory.UNCLEARED_BRAND_REFERENCE
        if ent.entity_type == EntityType.BRAND
        else FindingCategory.UNCLEARED_ORGANIZATION_REFERENCE
    )
    out.append(
        Finding(
            category=cat,
            severity=constraints.uncleared_reference_severity,
            entity=ent.name,
            entity_type=ent.entity_type,
            description=f"'{ent.name}' is a third-party {ent.entity_type.value.lower()} reference with no clearance on file.",
            remediation=f"Confirm product-placement license or negative-check clearance for '{ent.name}'.",
            source_api=ent.source_api,
            confidence=ent.confidence,
            timecodes=ent.timecodes,
        )
    )
    return out


def _evaluate_person(ent: DetectedEntity, assessments: dict[str, object]) -> list[Finding]:
    assessment = assessments.get(normalize_name(ent.name))
    if assessment is not None:
        # LLM script analysis vetted this name.
        if not assessment.is_real_living_person:  # type: ignore[attr-defined]
            return []  # fictional character — no right-of-publicity exposure
        sev = assessment.portrayal_risk  # type: ignore[attr-defined]
        return [
            Finding(
                category=FindingCategory.RIGHT_OF_PUBLICITY,
                severity=sev if sev.rank >= Severity.MEDIUM.rank else Severity.MEDIUM,
                entity=ent.name,
                entity_type=EntityType.PERSON,
                description=(
                    f"'{ent.name}' assessed as a real living person"
                    f"{' and public figure' if assessment.is_public_figure else ''}: "  # type: ignore[attr-defined]
                    f"{assessment.rationale}"  # type: ignore[attr-defined]
                ),
                remediation=(
                    "Obtain written release, rely on documented First Amendment/docudrama "
                    "counsel opinion, or rename the character."
                ),
                source_api=SourceApi.GEMINI_SCRIPT_ANALYSIS,
                requires_human_review=True,
            )
        ]
    # No LLM assessment available: surface as a low-severity candidate, never
    # auto-escalated — a name alone is not evidence of a rights issue.
    return [
        Finding(
            category=FindingCategory.PERSON_CLEARANCE_CANDIDATE,
            severity=Severity.LOW,
            entity=ent.name,
            entity_type=EntityType.PERSON,
            description=f"Named person '{ent.name}' detected; not yet assessed against living-person registry.",
            remediation="Run script analysis or manually verify against clearance/negative-check lists.",
            source_api=ent.source_api,
        )
    ]


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------
def compute_verdict(findings: list[Finding], failures: list[StageFailure]) -> Verdict:
    """FAILED > BLOCKED (CRITICAL/HIGH) > CONDITIONAL_CLEARANCE (MEDIUM) > CLEARED.

    A failed stage can never yield a clearance — the asset simply was not
    fully vetted. LOW and INFO findings are advisory (e.g. unassessed person
    names) and never change the verdict; they remain itemized on the report."""
    if failures:
        return Verdict.FAILED
    ranks = [f.severity.rank for f in findings if f.category != FindingCategory.SPONSOR_VERIFIED]
    if any(r >= Severity.HIGH.rank for r in ranks):
        return Verdict.BLOCKED
    if any(r >= Severity.MEDIUM.rank for r in ranks):
        return Verdict.CONDITIONAL_CLEARANCE
    return Verdict.CLEARED


def recompute_verdict_with_resolutions(
    findings: list[Finding],
    failures: list[StageFailure],
    resolutions: dict[str, HITLStatus],
) -> Verdict:
    """Recompute a verdict after human review: APPROVED findings are waived,
    ENFORCED and unresolved findings keep their severity."""
    effective = [
        f for f in findings
        if resolutions.get(f.hitl_token or "", None) != HITLStatus.APPROVED
    ]
    return compute_verdict(effective, failures)
