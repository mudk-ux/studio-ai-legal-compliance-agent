"""Cloud Video Intelligence logo recognition with correct timecode math.

(The legacy implementation formatted every offset as 00:00:SS, so a logo at
2m28s reported as 00:00:148. Offsets here are converted properly to
HH:MM:SS.mmm.)
"""

from __future__ import annotations

from ..observability import trace_span
from ..schemas import DetectedEntity, EntityType, SourceApi, TimecodeRange
from ..storage import is_gcs_uri
from .base import PerceptionError


def format_timecode(total_seconds: float) -> str:
    if total_seconds < 0:
        total_seconds = 0.0
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"


def _offset_seconds(duration) -> float:
    return duration.total_seconds() if hasattr(duration, "total_seconds") else (
        getattr(duration, "seconds", 0) + getattr(duration, "nanos", 0) / 1e9
    )


class VideoClient:
    def __init__(self, operation_timeout_s: int = 600):
        self.operation_timeout_s = operation_timeout_s

    def scan_video(self, video_uri: str) -> list[DetectedEntity]:
        """Run LOGO_RECOGNITION over a gs:// video. Returns one entity per brand
        with every tracked appearance as a timecode range."""
        try:
            from google.cloud import videointelligence_v1 as vi
        except ImportError as exc:
            raise PerceptionError("video_intelligence", "google-cloud-videointelligence is not installed", exc) from exc

        if not is_gcs_uri(video_uri):
            raise PerceptionError(
                "video_intelligence",
                f"Video Intelligence requires a gs:// URI (got {video_uri!r}); "
                "upload the asset to your staging bucket first.",
            )

        entities: dict[str, DetectedEntity] = {}
        with trace_span("video_scan_logos", video=video_uri):
            try:
                client = vi.VideoIntelligenceServiceClient()
                operation = client.annotate_video(
                    request={
                        "features": [vi.Feature.LOGO_RECOGNITION],
                        "input_uri": video_uri,
                    }
                )
                result = operation.result(timeout=self.operation_timeout_s)
                annotation_result = result.annotation_results[0]
                for logo in annotation_result.logo_recognition_annotations:
                    name = logo.entity.description
                    confidences: list[float] = []
                    timecodes: list[TimecodeRange] = []
                    for track in logo.tracks:
                        confidences.append(track.confidence)
                        timecodes.append(
                            TimecodeRange(
                                start=format_timecode(_offset_seconds(track.segment.start_time_offset)),
                                end=format_timecode(_offset_seconds(track.segment.end_time_offset)),
                            )
                        )
                    if name in entities:
                        entities[name].timecodes.extend(timecodes)
                    else:
                        entities[name] = DetectedEntity(
                            name=name,
                            entity_type=EntityType.BRAND,
                            source_api=SourceApi.GCP_VIDEO_INTELLIGENCE,
                            confidence=round(max(confidences), 4) if confidences else None,
                            timecodes=timecodes,
                        )
            except PerceptionError:
                raise
            except Exception as exc:
                raise PerceptionError("video_intelligence", f"scan_video failed: {exc}", exc) from exc

        return list(entities.values())
