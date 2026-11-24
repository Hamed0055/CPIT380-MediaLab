"""Load supported uploads and encode PNG downloads without temporary files."""

from io import BytesIO
from pathlib import Path
import re

from PIL import Image, ImageOps, UnidentifiedImageError


UPLOAD_TYPES = ["png", "jpg", "jpeg", "bmp", "webp", "gif", "tif", "tiff"]
FORMATS = {"PNG", "JPEG", "BMP", "WEBP", "GIF", "TIFF"}
MAX_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 12_000_000
MAX_SIDE = 6000


# Read image: Check the actual file format and size before decoding its first frame.
def read_image(payload: bytes) -> Image.Image:
    if not payload or len(payload) > MAX_BYTES:
        raise ValueError("Choose an image file between 1 byte and 20 MB.")
    try:
        with Image.open(BytesIO(payload)) as loaded:
            if loaded.format not in FORMATS:
                raise ValueError("Unsupported image format. Choose PNG, JPEG, BMP, WebP, GIF or TIFF.")
            if loaded.width * loaded.height > MAX_PIXELS or max(loaded.size) > MAX_SIDE:
                raise ValueError("Use an image up to 12 megapixels and 6000 pixels per side.")
            oriented = ImageOps.exif_transpose(loaded)
            has_alpha = "A" in oriented.getbands() or "transparency" in oriented.info
            return oriented.convert("RGBA" if has_alpha else "RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("The upload is not a readable supported image.") from exc


# PNG bytes: Save a Pillow image to an in-memory buffer for preview or download.
def png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


# Download name: Use the source stem with a safe operation suffix.
def download_name(source_name: str, operation: str) -> str:
    stem = Path(source_name.replace("\\", "/")).stem
    stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", stem).strip("-_")[:64] or "image"
    suffix = re.sub(r"[^a-z0-9]+", "-", operation.lower()).strip("-") or "result"
    return f"{stem}-{suffix}.png"
