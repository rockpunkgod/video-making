"""Verify supplied image bytes and bind external visual assertions to a draft.

No filesystem/network resolution, OCR, handwriting classification or grading.
Decoded images prove payload integrity, not original authorship or human review.
"""
import base64
import hashlib
from io import BytesIO
import warnings
from PIL import Image, UnidentifiedImageError

MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 20_000_000


def image_manifest(question):
    result = []
    seen = set()
    for asset in question.get('original_images', []):
        if asset['image_id'] in seen:
            raise ValueError('Duplicate original image ID')
        seen.add(asset['image_id'])
        encoded = asset['data_base64']
        if len(encoded) > (MAX_BYTES + 2) // 3 * 4:
            raise ValueError('Original image exceeds byte limit')
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, base64.binascii.Error) as exc:
            raise ValueError('Invalid original image base64') from exc
        if not raw or len(raw) > MAX_BYTES:
            raise ValueError('Original image exceeds byte limit or is empty')
        digest = hashlib.sha256(raw).hexdigest()
        if digest != asset['sha256']:
            raise ValueError('Original image hash mismatch')
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(BytesIO(raw)) as image:
                    actual = {'PNG': 'image/png', 'JPEG': 'image/jpeg'}.get(image.format)
                    width, height = image.size
                    if actual != asset['mime_type'] or actual is None:
                        raise ValueError('Original image MIME mismatch or unsupported format')
                    if width * height > MAX_PIXELS:
                        raise ValueError('Original image exceeds pixel limit')
                    if getattr(image, 'n_frames', 1) != 1:
                        raise ValueError('Original image must be a single frame')
                    image.verify()
                with Image.open(BytesIO(raw)) as image:
                    image.load()  # A header or filename alone is not an image.
        except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError,
                Image.DecompressionBombWarning) as exc:
            raise ValueError('Invalid or unsafe original image payload') from exc
        result.append({'image_id': asset['image_id'], 'sha256': digest,
                       'mime_type': actual, 'width': width, 'height': height})
    return result


def check_image_region(region, manifest):
    asset = next((a for a in manifest if a['image_id'] == region['image_id']), None)
    if asset is None or asset['sha256'] != region['sha256']:
        raise ValueError('Image evidence must identify a verified original-image payload')
    x1, y1, x2, y2 = region['box']
    if not 0 <= x1 < x2 <= asset['width'] or not 0 <= y1 < y2 <= asset['height']:
        raise ValueError('Image evidence region is outside original-image bounds')
    return region
