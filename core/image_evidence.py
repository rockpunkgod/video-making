"""Compatibility entry point for source-bound image validation.

Keep local limits patchable by existing writing callers/tests. The portable
implementation has no dependency on core, Registry, OCR or an answer engine.
"""
from video_contracts.image_evidence import (
    image_manifest as _image_manifest, check_image_region,
    MAX_BYTES, MAX_PIXELS,
)


def image_manifest(question):
    return _image_manifest(question, max_bytes=MAX_BYTES, max_pixels=MAX_PIXELS)
