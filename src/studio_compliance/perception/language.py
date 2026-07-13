"""Cloud Natural Language entity extraction for screenplay text.

Long scripts are chunked under the API's request-size limit and results are
merged — the whole document is analyzed, unlike naive truncation which would
silently skip Act 2 of a feature script.
"""

from __future__ import annotations

from ..observability import trace_span
from ..schemas import DetectedEntity, EntityType, SourceApi
from .base import PerceptionError

_TYPE_MAP = {
    "PERSON": EntityType.PERSON,
    "ORGANIZATION": EntityType.ORGANIZATION,
    "CONSUMER_GOOD": EntityType.BRAND,
    "LOCATION": EntityType.LOCATION,
}


def keep_entity(entity_type: EntityType, proper_mentions: int) -> bool:
    """Brand-like entities must have at least one PROPER-noun mention.

    The live NL API returns common nouns ('bread', 'sofa', 'piano') as
    CONSUMER_GOOD entities; without this gate every household object in a
    period play becomes an 'uncleared brand'. Persons/locations are kept
    regardless — downstream policy treats them differently.
    """
    if entity_type in (EntityType.ORGANIZATION, EntityType.BRAND):
        return proper_mentions > 0
    return True


def _chunk_text(text: str, max_bytes: int) -> list[str]:
    """Split on paragraph boundaries keeping each chunk under max_bytes (UTF-8)."""
    if len(text.encode("utf-8")) <= max_bytes:
        return [text]
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for para in text.split("\n\n"):
        size = len(para.encode("utf-8")) + 2
        if size > max_bytes:  # pathological single paragraph: hard split
            for i in range(0, len(para), max_bytes // 4):
                chunks.append(para[i : i + max_bytes // 4])
            continue
        if current_size + size > max_bytes:
            chunks.append("\n\n".join(current))
            current, current_size = [], 0
        current.append(para)
        current_size += size
    if current:
        chunks.append("\n\n".join(current))
    return chunks


class LanguageClient:
    def __init__(self, chunk_bytes: int = 900_000):
        self.chunk_bytes = chunk_bytes

    def analyze_entities(self, text: str) -> list[DetectedEntity]:
        try:
            from google.cloud import language_v1
        except ImportError as exc:
            raise PerceptionError("natural_language", "google-cloud-language is not installed", exc) from exc

        merged: dict[tuple[str, EntityType], DetectedEntity] = {}
        proper_counts: dict[tuple[str, EntityType], int] = {}
        chunks = _chunk_text(text, self.chunk_bytes)

        with trace_span("nl_analyze_entities", chunks=len(chunks), text_bytes=len(text.encode("utf-8"))):
            try:
                client = language_v1.LanguageServiceClient()
                for chunk in chunks:
                    document = language_v1.Document(
                        content=chunk, type_=language_v1.Document.Type.PLAIN_TEXT
                    )
                    response = client.analyze_entities(document=document)
                    for entity in response.entities:
                        etype = _TYPE_MAP.get(entity.type_.name)
                        if etype is None:
                            continue
                        key = (entity.name.casefold(), etype)
                        linked = bool(dict(entity.metadata).get("wikipedia_url") or dict(entity.metadata).get("mid"))
                        proper_counts[key] = proper_counts.get(key, 0) + sum(
                            1 for m in entity.mentions if m.type_.name == "PROPER"
                        )
                        if key in merged:
                            existing = merged[key]
                            existing.mention_count += len(entity.mentions) or 1
                            existing.salience = max(existing.salience or 0.0, entity.salience)
                            existing.knowledge_linked = existing.knowledge_linked or linked
                        else:
                            merged[key] = DetectedEntity(
                                name=entity.name,
                                entity_type=etype,
                                source_api=SourceApi.GCP_NATURAL_LANGUAGE,
                                salience=entity.salience,
                                mention_count=len(entity.mentions) or 1,
                                knowledge_linked=linked,
                            )
            except PerceptionError:
                raise
            except Exception as exc:
                raise PerceptionError("natural_language", f"analyze_entities failed: {exc}", exc) from exc

        kept = [
            entity
            for key, entity in merged.items()
            if keep_entity(entity.entity_type, proper_counts.get(key, 0))
        ]
        return sorted(kept, key=lambda e: -(e.salience or 0.0))
