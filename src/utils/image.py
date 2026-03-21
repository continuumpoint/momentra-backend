import io
from PIL import Image
from fastapi import HTTPException, status
from src.config.settings import get_settings

settings = get_settings()

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def validate_image_file(content_type: str, filename: str) -> None:
    """Validate that uploaded file is a genuine image."""
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid file type: {content_type}. Only JPEG, PNG, WebP, GIF allowed.",
        )
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid file extension: {ext}",
        )


def compress_image(raw_bytes: bytes) -> bytes:
    """
    Compress image to JPEG at configured quality.
    Returns compressed bytes.
    """
    try:
        img = Image.open(io.BytesIO(raw_bytes))
        # Convert to RGB (handles RGBA, P-mode PNGs, etc.)
        if img.mode in ("RGBA", "P", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        output = io.BytesIO()
        img.save(output, format="JPEG", quality=settings.JPEG_COMPRESSION_QUALITY, optimize=True)
        return output.getvalue()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Image processing failed: {str(exc)}",
        )


def verify_image_content(raw_bytes: bytes) -> None:
    """Verify bytes actually represent a valid image (prevents disguised uploads)."""
    try:
        img = Image.open(io.BytesIO(raw_bytes))
        img.verify()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File content is not a valid image.",
        )
