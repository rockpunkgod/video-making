"""Pure image-payload checks shared by producers and portable consumers.

No OCR, filesystem resolution, chart interpretation or review certification.
"""
import base64
import hashlib
from io import BytesIO
import warnings

MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 20_000_000


def image_manifest(question, *, max_bytes=MAX_BYTES, max_pixels=MAX_PIXELS):
    # Text-only portable consumers retain their old dependency boundary.
    from PIL import Image, UnidentifiedImageError
    result, seen = [], set()
    for asset in question.get('original_images', []):
        if asset['image_id'] in seen:
            raise ValueError('Duplicate original image ID')
        seen.add(asset['image_id'])
        encoded = asset['data_base64']
        if not isinstance(encoded, str) or len(encoded) > (max_bytes + 2) // 3 * 4:
            raise ValueError('Original image exceeds byte limit')
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, base64.binascii.Error) as exc:
            raise ValueError('Invalid original image base64') from exc
        if not raw or len(raw) > max_bytes:
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
                    if width * height > max_pixels:
                        raise ValueError('Original image exceeds pixel limit')
                    if getattr(image, 'n_frames', 1) != 1:
                        raise ValueError('Original image must be a single frame')
                    image.verify()
                with Image.open(BytesIO(raw)) as image:
                    image.load()
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
    box = region['box']
    if (not isinstance(box, list) or len(box) != 4
            or any(type(value) is not int for value in box)):
        raise ValueError('Image evidence box requires four integer pixel coordinates')
    x1, y1, x2, y2 = box
    if not 0 <= x1 < x2 <= asset['width'] or not 0 <= y1 < y2 <= asset['height']:
        raise ValueError('Image evidence region is outside original-image bounds')
    return region
