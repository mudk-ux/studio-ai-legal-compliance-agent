from conftest import (
    fictional_assessment,
    living_person_assessment,
    logo,
    org,
    person,
    video_brand,
)
from studio_compliance.policy import (
    compute_verdict,
    evaluate_entities,
    normalize_name,
    recompute_verdict_with_resolutions,
    scan_script_for_rule_entities,
    scan_text_for_terms,
    substance_category,
)
from studio_compliance.schemas import (
    ExclusivityDeal,
    FindingCategory,
    HITLStatus,
    IntakeConstraints,
    ScriptAnalysis,
    Severity,
    SourceApi,
    StageFailure,
    Verdict,
)


def constraints(sponsor=None, restricted=(), rating="TV-PG"):
    return IntakeConstraints(
        target_rating=rating,
        exclusivity_deals=ExclusivityDeal(
            primary_sponsor=sponsor, restricted_competitors=list(restricted)
        ),
    )


# ---------------------------------------------------------------------------
# Normalization & aliases
# ---------------------------------------------------------------------------
def test_normalize_strips_punctuation_case_and_possessives():
    assert normalize_name("DUNKIN' DOUGHNUTS") == "dunkin donuts"
    assert normalize_name("Dunkin’ Donuts") == "dunkin donuts"
    assert normalize_name("Victoria's Secret") == "victoria secret"
    assert normalize_name("Coca Cola") == "coca-cola"


def test_substance_categories():
    assert substance_category("Vuse Alto") == "TOBACCO_VAPE"
    assert substance_category("Winston Cigarettes") == "TOBACCO"
    assert substance_category("Nike") is None


def test_scan_text_for_terms_whole_words_only():
    assert scan_text_for_terms("I admit nothing", ["MIT"]) == []
    assert scan_text_for_terms("He went to MIT last year", ["MIT"]) == ["MIT"]


# ---------------------------------------------------------------------------
# Exclusivity
# ---------------------------------------------------------------------------
def test_restricted_competitor_is_critical_breach():
    findings = evaluate_entities([org("Facebook")], constraints("Starbucks", ["Facebook"]))
    assert len(findings) == 1
    assert findings[0].category == FindingCategory.SPONSOR_EXCLUSIVITY_BREACH
    assert findings[0].severity == Severity.CRITICAL
    assert findings[0].requires_human_review


def test_alias_match_dunkin_doughnuts_vs_donuts():
    findings = evaluate_entities(
        [org("DUNKIN' DOUGHNUTS")], constraints("Starbucks", ["Dunkin' Donuts"])
    )
    assert findings[0].category == FindingCategory.SPONSOR_EXCLUSIVITY_BREACH


def test_primary_sponsor_is_info_not_violation():
    findings = evaluate_entities([logo("Nike")], constraints("Nike", ["Adidas"]))
    assert findings[0].category == FindingCategory.SPONSOR_VERIFIED
    assert findings[0].severity == Severity.INFO


def test_unrelated_org_is_uncleared_reference_medium():
    findings = evaluate_entities([org("Harvard")], constraints("Starbucks", ["Dunkin' Donuts"]))
    assert findings[0].category == FindingCategory.UNCLEARED_ORGANIZATION_REFERENCE
    assert findings[0].severity == Severity.MEDIUM


def test_person_named_like_competitor_does_not_trip_brand_rule():
    # 'Worthing' listed as a restricted competitor must not match a PERSON entity.
    findings = evaluate_entities([person("Worthing")], constraints("X", ["Worthing"]))
    assert all(f.category != FindingCategory.SPONSOR_EXCLUSIVITY_BREACH for f in findings)


# ---------------------------------------------------------------------------
# Constraint-term scan (NER-independent; live NL API misses all-caps action
# lines and lowercase prop notes — observed against the live NL API, 2026-07)
# ---------------------------------------------------------------------------
def test_term_scan_catches_allcaps_alias_ner_missed():
    text = "He waits in the Cadillac with two cups of DUNKIN' DOUGHNUTS coffee."
    ents = scan_script_for_rule_entities(text, constraints("Starbucks", ["Dunkin' Donuts"]), [])
    assert [e.name for e in ents] == ["Dunkin' Donuts"]
    assert ents[0].source_api == SourceApi.DETERMINISTIC_TEXT_SCAN
    findings = evaluate_entities(ents, constraints("Starbucks", ["Dunkin' Donuts"]))
    assert findings[0].category == FindingCategory.SPONSOR_EXCLUSIVITY_BREACH


def test_term_scan_catches_lowercase_restricted_term():
    text = "She carries an apple device prop in her pack."
    ents = scan_script_for_rule_entities(text, constraints("Sony", ["Apple"]), [])
    assert [e.name for e in ents] == ["Apple"]


def test_term_scan_apples_plural_is_not_apple():
    # 'DO YOU LIKE APPLES?' (fruit) must not match restricted 'Apple'.
    text = "DO YOU LIKE APPLES?! WELL I GOT HER NUMBER. HOW DO YOU LIKE THEM APPLES?"
    assert scan_script_for_rule_entities(text, constraints("Sony", ["Apple"]), []) == []


def test_term_scan_suppressed_when_term_is_a_person_in_document():
    text = "WORTHING enters. Jack Worthing bows to Lady Bracknell."
    ents = scan_script_for_rule_entities(
        text, constraints("X", ["Worthing", "Bracknell"]),
        [person("Jack Worthing"), person("Lady Bracknell")],
    )
    assert ents == []


def test_term_scan_honorific_marks_term_as_character_even_without_ner_person():
    # Round-2 live regression: NL never typed Lady Bracknell as PERSON, so the
    # term scan flagged 'Bracknell' as a CRITICAL breach. The honorific pass
    # must recognize '<honorific> <Term>' as a character name on its own.
    text = "LADY BRACKNELL enters the drawing room. Lady Bracknell sits."
    ents = scan_script_for_rule_entities(text, constraints("General Mills", ["Bracknell"]), [])
    assert [e.entity_type.value for e in ents] == ["PERSON"]
    assert ents[0].name == "Lady Bracknell"
    findings = evaluate_entities(ents, constraints("General Mills", ["Bracknell"]))
    assert all(f.category != FindingCategory.SPONSOR_EXCLUSIVITY_BREACH for f in findings)
    assert compute_verdict(findings, []) == Verdict.CLEARED


def test_term_scan_honorific_does_not_shield_real_brand_terms():
    # 'Dunkin' never appears behind an honorific; the breach must survive.
    text = "Mr. Chuckie waits with two cups of DUNKIN' DOUGHNUTS coffee."
    ents = scan_script_for_rule_entities(text, constraints("Starbucks", ["Dunkin' Donuts"]), [])
    assert [e.name for e in ents] == ["Dunkin' Donuts"]


def test_term_scan_does_not_duplicate_ner_detection():
    text = "Facebook is everywhere."
    ents = scan_script_for_rule_entities(
        text, constraints("S", ["Facebook"]), [org("Facebook")]
    )
    assert ents == []


def test_term_scan_substance_requires_capitalization():
    lower = "the camel walked through the market"
    upper = "a CAMEL billboard looms over the market"
    assert scan_script_for_rule_entities(lower, constraints(), []) == []
    hits = scan_script_for_rule_entities(upper, constraints(), [])
    assert [e.name for e in hits] == ["Camel"]
    findings = evaluate_entities(hits, constraints(rating="TV-PG"))
    assert findings[0].category == FindingCategory.SP_SUBSTANCE_VIOLATION


# ---------------------------------------------------------------------------
# Screenplay structure suppression (live NL typed 'ACT III' / 'Enter Lane'
# as ORGANIZATION, blocking clearance of a clean period play)
# ---------------------------------------------------------------------------
def test_structure_terms_recognized():
    from studio_compliance.policy import is_screenplay_structure_term

    for term in ("ACT III", "FIRST ACT", "Scene 5", "Enter Lane", "Exeunt omnes", "Re-enter ALGERNON", "PROLOGUE"):
        assert is_screenplay_structure_term(term), term
    for term in ("Harvard", "Scene Systems Inc", "Entergy", "Facebook", "Acted Media"):
        assert not is_screenplay_structure_term(term), term


def test_structure_orgs_produce_no_findings_but_deal_terms_still_do():
    entities = [org("Enter Lane"), org("ACT III"), org("Facebook")]
    findings = evaluate_entities(entities, constraints("S", ["Facebook"]))
    assert [f.entity for f in findings] == ["Facebook"]
    assert compute_verdict(findings, []) == Verdict.BLOCKED
    clean = evaluate_entities([org("Enter Lane"), org("FIRST ACT")], constraints())
    assert clean == [] and compute_verdict(clean, []) == Verdict.CLEARED


# ---------------------------------------------------------------------------
# NER misclassification guard (live NL tagged 'Manservant Lady Bracknell Hon'
# as ORGANIZATION, tripping a fake CRITICAL breach)
# ---------------------------------------------------------------------------
def test_org_overlapping_person_name_is_suppressed_from_brand_rules():
    entities = [org("Manservant Lady Bracknell Hon"), person("Lady Bracknell")]
    findings = evaluate_entities(entities, constraints("General Mills", ["Bracknell"]))
    assert all(f.category != FindingCategory.SPONSOR_EXCLUSIVITY_BREACH for f in findings)
    assert compute_verdict(findings, []) != Verdict.BLOCKED


# ---------------------------------------------------------------------------
# S&P substance gating
# ---------------------------------------------------------------------------
def test_vape_brand_blocks_under_tv_pg_regardless_of_deal():
    findings = evaluate_entities([logo("Vuse")], constraints("Gucci", ["Louis Vuitton"]))
    assert findings[0].category == FindingCategory.SP_SUBSTANCE_VIOLATION
    assert findings[0].severity == Severity.CRITICAL


def test_alcohol_allowed_at_tv_14_but_not_tv_pg():
    tv14 = evaluate_entities([org("Heineken")], constraints(rating="TV-14"))
    tvpg = evaluate_entities([org("Heineken")], constraints(rating="TV-PG"))
    assert all(f.category != FindingCategory.SP_SUBSTANCE_VIOLATION for f in tv14)
    assert tvpg[0].category == FindingCategory.SP_SUBSTANCE_VIOLATION


# ---------------------------------------------------------------------------
# Persons & LLM assessments
# ---------------------------------------------------------------------------
def test_person_without_assessment_is_low_candidate():
    findings = evaluate_entities([person("Gerald Lambeau")], constraints())
    assert findings[0].category == FindingCategory.PERSON_CLEARANCE_CANDIDATE
    assert findings[0].severity == Severity.LOW


def test_fictional_person_with_assessment_produces_no_finding():
    analysis = ScriptAnalysis(persons=[fictional_assessment("Gerald Lambeau")])
    findings = evaluate_entities([person("Gerald Lambeau")], constraints(), analysis)
    assert findings == []


def test_living_public_figure_is_right_of_publicity():
    analysis = ScriptAnalysis(persons=[living_person_assessment("Mark Zuckerberg")])
    findings = evaluate_entities([person("Mark Zuckerberg")], constraints(), analysis)
    assert findings[0].category == FindingCategory.RIGHT_OF_PUBLICITY
    assert findings[0].severity == Severity.HIGH
    assert findings[0].requires_human_review


# ---------------------------------------------------------------------------
# Timecodes -> VFX slates
# ---------------------------------------------------------------------------
def test_video_breach_gets_vfx_slate_with_real_timecodes():
    findings = evaluate_entities([video_brand("Sony")], constraints("Apple", ["Sony"]))
    breach = findings[0]
    assert breach.vfx_slates[0].start_timecode == "00:02:28.000"
    assert breach.vfx_slates[0].end_timecode == "00:02:35.500"


# ---------------------------------------------------------------------------
# Verdict ladder
# ---------------------------------------------------------------------------
def test_verdict_ladder():
    crit = evaluate_entities([org("Facebook")], constraints("S", ["Facebook"]))
    med = evaluate_entities([org("Harvard")], constraints())
    low = evaluate_entities([person("Gerald Lambeau")], constraints())
    assert compute_verdict(crit, []) == Verdict.BLOCKED
    assert compute_verdict(med, []) == Verdict.CONDITIONAL_CLEARANCE
    # LOW findings are advisory (unassessed person candidates): a period play
    # full of character names must still be able to clear.
    assert low and compute_verdict(low, []) == Verdict.CLEARED
    assert compute_verdict([], []) == Verdict.CLEARED


def test_failure_always_wins_even_with_no_findings():
    assert compute_verdict([], [StageFailure(stage="vision", error="quota")]) == Verdict.FAILED
    crit = evaluate_entities([org("Facebook")], constraints("S", ["Facebook"]))
    assert compute_verdict(crit, [StageFailure(stage="x", error="y")]) == Verdict.FAILED


def test_sponsor_verified_info_does_not_block_clearance():
    findings = evaluate_entities([logo("Nike")], constraints("Nike"))
    assert compute_verdict(findings, []) == Verdict.CLEARED


def test_recompute_after_hitl_approval_waives_finding():
    findings = evaluate_entities([org("Facebook")], constraints("S", ["Facebook"]))
    findings[0].hitl_token = "HITL-TEST1"
    assert compute_verdict(findings, []) == Verdict.BLOCKED
    verdict = recompute_verdict_with_resolutions(
        findings, [], {"HITL-TEST1": HITLStatus.APPROVED}
    )
    assert verdict == Verdict.CLEARED
    verdict_enforced = recompute_verdict_with_resolutions(
        findings, [], {"HITL-TEST1": HITLStatus.ENFORCED}
    )
    assert verdict_enforced == Verdict.BLOCKED
