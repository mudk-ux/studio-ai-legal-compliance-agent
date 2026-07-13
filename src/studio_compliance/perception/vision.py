"""Cloud Vision logo detection + OCR for set/wardrobe/prop stills.

Logo detections come back with the API's real confidence score. OCR text is
returned as raw evidence so the policy layer can scan it for rule terms
(catching printed brand names the logo model misses, e.g. 'Vuse' on a vape
pen barrel) — with provenance marked as OCR, never inflated into a fake
logo detection.
"""

from __future__ import annotations

from ..observability import trace_span
from ..schemas import DetectedEntity, EntityType, SourceApi
from ..storage import is_gcs_uri, read_bytes
from .base import PerceptionError


class VisionResult:
    def __init__(self, logos: list[DetectedEntity], ocr_text: str):
        self.logos = logos
        self.ocr_text = ocr_text


class VisionClient:
    def scan_image(self, image_uri: str) -> VisionResult:
        try:
            from google.cloud import vision
        except ImportError as exc:
            raise PerceptionError("vision", "google-cloud-vision is not installed", exc) from exc

        with trace_span("vision_scan_image", image=image_uri):
            try:
                client = vision.ImageAnnotatorClient()
                if is_gcs_uri(image_uri):
                    image = vision.Image(source=vision.ImageSource(gcs_image_uri=image_uri))
                else:
                    image = vision.Image(content=read_bytes(image_uri))

                logo_response = client.logo_detection(image=image)
                if logo_response.error.message:
                    raise PerceptionError("vision", f"logo_detection: {logo_response.error.message}")

                logos = [
                    DetectedEntity(
                        name=annotation.description,
                        entity_type=EntityType.BRAND,
                        source_api=SourceApi.GCP_VISION_LOGO,
                        confidence=round(annotation.score, 4),
                    )
                    for annotation in logo_response.logo_annotations
                ]

                text_response = client.text_detection(image=image)
                if text_response.error.message:
                    raise PerceptionError("vision", f"text_detection: {text_response.error.message}")
                ocr_text = (
                    text_response.text_annotations[0].description
                    if text_response.text_annotations
                    else ""
                )
            except PerceptionError:
                raise
            except Exception as exc:
                raise PerceptionError("vision", f"scan_image failed: {exc}", exc) from exc

        return VisionResult(logos=logos, ocr_text=ocr_text)
