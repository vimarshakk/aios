"""Image data and processing — load, resize, crop, convert images.

Provides ImageData as an immutable container and ImageProcessor
for operations. Uses stdlib only (no PIL dependency) for basic
operations, with optional PIL support for advanced processing.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ImageFormat(StrEnum):
    """Supported image formats."""

    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"
    BMP = "bmp"
    GIF = "gif"
    UNKNOWN = "unknown"


class ResizeMode(StrEnum):
    """Image resize strategy."""

    FIT = "fit"  # Fit within bounds, preserve aspect ratio
    FILL = "fill"  # Fill bounds, crop excess
    STRETCH = "stretch"  # Stretch to exact dimensions


@dataclass(frozen=True)
class ImageData:
    """Immutable image container.

    Attributes:
        raw: Raw image bytes.
        format: Detected image format.
        width: Image width in pixels (0 if unknown).
        height: Image height in pixels (0 if unknown).
        source: Original source path or URL.
        checksum: SHA-256 hash of the raw bytes.
    """

    raw: bytes
    format: ImageFormat = ImageFormat.UNKNOWN
    width: int = 0
    height: int = 0
    source: str = ""
    checksum: str = ""

    @classmethod
    def from_bytes(
        cls, data: bytes, source: str = "", width: int = 0, height: int = 0
    ) -> ImageData:
        """Create from raw bytes."""
        fmt = _detect_format(data)
        checksum = hashlib.sha256(data).hexdigest()
        return cls(
            raw=data,
            format=fmt,
            width=width,
            height=height,
            source=source,
            checksum=checksum,
        )

    @classmethod
    def from_file(cls, path: str | Path) -> ImageData:
        """Load from a file path."""
        p = Path(path)
        data = p.read_bytes()
        return cls.from_bytes(data, source=str(p))

    @classmethod
    def from_base64(cls, b64: str, source: str = "") -> ImageData:
        """Decode from base64 string."""
        raw = base64.b64decode(b64)
        return cls.from_bytes(raw, source=source)

    def to_base64(self) -> str:
        """Encode to base64 string."""
        return base64.b64encode(self.raw).decode("ascii")

    @property
    def size_bytes(self) -> int:
        """Size in bytes."""
        return len(self.raw)

    @property
    def mime_type(self) -> str:
        """MIME type string."""
        _map = {
            ImageFormat.PNG: "image/png",
            ImageFormat.JPEG: "image/jpeg",
            ImageFormat.WEBP: "image/webp",
            ImageFormat.BMP: "image/bmp",
            ImageFormat.GIF: "image/gif",
        }
        return _map.get(self.format, "application/octet-stream")


@dataclass(frozen=True)
class ResizeResult:
    """Result of a resize operation.

    Attributes:
        ok: Whether the operation succeeded.
        image: Resized image data (if successful).
        original_size: (width, height) before resize.
        new_size: (width, height) after resize.
        error: Error message if failed.
    """

    ok: bool
    image: ImageData | None = None
    original_size: tuple[int, int] = (0, 0)
    new_size: tuple[int, int] = (0, 0)
    error: str | None = None


@dataclass(frozen=True)
class ColorInfo:
    """Color analysis result.

    Attributes:
        hex_color: Hex color string (e.g. "#ff0000").
        r: Red channel (0-255).
        g: Green channel (0-255).
        b: Blue channel (0-255).
        name: Human-readable color name (if known).
    """

    hex_color: str = "#000000"
    r: int = 0
    g: int = 0
    b: int = 0
    name: str = ""


class ImageProcessor:
    """Image processing operations.

    Provides basic operations using only stdlib (struct for PNG parsing).
    For advanced operations (resize, crop), delegates to PIL if available.

    Usage::

        proc = ImageProcessor()
        img = ImageData.from_file("photo.png")
        resized = await proc.resize(img, 800, 600)
    """

    def __init__(self) -> None:
        self._has_pil = _check_pil()

    @property
    def has_pil(self) -> bool:
        """Whether PIL/Pillow is available for advanced operations."""
        return self._has_pil

    async def resize(
        self,
        image: ImageData,
        width: int,
        height: int,
        mode: ResizeMode = ResizeMode.FIT,
    ) -> ResizeResult:
        """Resize an image.

        Falls back to simple bilinear scaling if PIL is not available.
        """
        if not self._has_pil:
            return ResizeResult(
                ok=False,
                original_size=(image.width, image.height),
                error="Pillow not installed. Install with: pip install Pillow",
            )
        try:
            import io

            from PIL import Image as PILImage

            pil_img = PILImage.open(io.BytesIO(image.raw))
            original = (pil_img.width, pil_img.height)

            if mode == ResizeMode.FIT:
                pil_img.thumbnail((width, height), PILImage.Resampling.LANCZOS)
            elif mode == ResizeMode.FILL:
                pil_img = _crop_fill(pil_img, width, height)
            else:
                pil_img = pil_img.resize((width, height), PILImage.Resampling.LANCZOS)

            buf = io.BytesIO()
            fmt_map = {
                ImageFormat.PNG: "PNG",
                ImageFormat.JPEG: "JPEG",
                ImageFormat.WEBP: "WEBP",
            }
            save_fmt = fmt_map.get(image.format, "PNG")
            pil_img.save(buf, format=save_fmt)
            new_raw = buf.getvalue()

            return ResizeResult(
                ok=True,
                image=ImageData.from_bytes(
                    new_raw,
                    source=image.source,
                    width=pil_img.width,
                    height=pil_img.height,
                ),
                original_size=original,
                new_size=(pil_img.width, pil_img.height),
            )
        except Exception as exc:
            return ResizeResult(
                ok=False,
                original_size=(image.width, image.height),
                error=str(exc),
            )

    async def get_color_at(
        self, image: ImageData, x: int, y: int
    ) -> ColorInfo | None:
        """Get the color of a pixel. Requires PIL."""
        if not self._has_pil:
            return None
        try:
            import io

            from PIL import Image as PILImage

            pil_img = PILImage.open(io.BytesIO(image.raw))
            if x >= pil_img.width or y >= pil_img.height:
                return None
            pixel = pil_img.getpixel((x, y))
            r, g, b = pixel[0], pixel[1], pixel[2]
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            name = _color_name(r, g, b)
            return ColorInfo(hex_color=hex_color, r=r, g=g, b=b, name=name)
        except Exception:
            return None

    async def get_dominant_colors(
        self, image: ImageData, count: int = 5
    ) -> list[ColorInfo]:
        """Get dominant colors via simple quantization. Requires PIL."""
        if not self._has_pil:
            return []
        try:
            import io

            from PIL import Image as PILImage

            pil_img = PILImage.open(io.BytesIO(image.raw)).convert("RGB")
            small = pil_img.resize((100, 100), PILImage.Resampling.LANCZOS)
            pixels = list(small.getdata())
            # Simple color bucketing
            buckets: dict[tuple[int, int, int], int] = {}
            for r, g, b in pixels:
                # Quantize to 32-level
                key = (r // 32 * 32, g // 32 * 32, b // 32 * 32)
                buckets[key] = buckets.get(key, 0) + 1
            sorted_colors = sorted(buckets.items(), key=lambda x: x[1], reverse=True)
            result = []
            for (r, g, b), _count in sorted_colors[:count]:
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                name = _color_name(r, g, b)
                result.append(ColorInfo(hex_color=hex_color, r=r, g=g, b=b, name=name))
            return result
        except Exception:
            return []

    async def crop(
        self, image: ImageData, x: int, y: int, w: int, h: int
    ) -> ResizeResult:
        """Crop a region from the image. Requires PIL."""
        if not self._has_pil:
            return ResizeResult(
                ok=False,
                original_size=(image.width, image.height),
                error="Pillow not installed",
            )
        try:
            import io

            from PIL import Image as PILImage

            pil_img = PILImage.open(io.BytesIO(image.raw))
            original = (pil_img.width, pil_img.height)
            cropped = pil_img.crop((x, y, x + w, y + h))
            buf = io.BytesIO()
            pil_img.format = pil_img.format or "PNG"
            cropped.save(buf, format=pil_img.format or "PNG")
            new_raw = buf.getvalue()
            return ResizeResult(
                ok=True,
                image=ImageData.from_bytes(
                    new_raw, source=image.source, width=w, height=h
                ),
                original_size=original,
                new_size=(w, h),
            )
        except Exception as exc:
            return ResizeResult(
                ok=False,
                original_size=(image.width, image.height),
                error=str(exc),
            )


def _detect_format(data: bytes) -> ImageFormat:
    """Detect image format from magic bytes."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ImageFormat.PNG
    if data[:2] == b"\xff\xd8":
        return ImageFormat.JPEG
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ImageFormat.WEBP
    if data[:2] == b"BM":
        return ImageFormat.BMP
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ImageFormat.GIF
    return ImageFormat.UNKNOWN


def _check_pil() -> bool:
    try:
        from PIL import Image  # noqa: F401

        return True
    except ImportError:
        return False


def _crop_fill(img: object, target_w: int, target_h: int) -> object:
    """Center-crop to fill target dimensions."""
    from PIL import Image as PILImage

    img = img  # type: ignore[reportUnannotatedClassDefinition]
    src_w, src_h = img.width, img.height  # type: ignore[union-attr]
    ratio = max(target_w / src_w, target_h / src_h)
    new_w = int(src_w * ratio)
    new_h = int(src_h * ratio)
    img = img.resize((new_w, new_h), PILImage.Resampling.LANCZOS)  # type: ignore[union-attr]
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))  # type: ignore[union-attr]


# Simple color name mapping for common colors
_COLOR_NAMES = [
    (0, 0, 0, "black"),
    (255, 255, 255, "white"),
    (255, 0, 0, "red"),
    (0, 255, 0, "green"),
    (0, 0, 255, "blue"),
    (255, 255, 0, "yellow"),
    (255, 0, 255, "magenta"),
    (0, 255, 255, "cyan"),
    (128, 128, 128, "gray"),
    (192, 192, 192, "silver"),
    (128, 0, 0, "maroon"),
    (0, 128, 0, "dark green"),
    (0, 0, 128, "navy"),
    (255, 165, 0, "orange"),
    (128, 0, 128, "purple"),
]


def _color_name(r: int, g: int, b: int) -> str:
    """Get a human-readable name for a color."""
    best_name = ""
    best_dist = float("inf")
    for cr, cg, cb, name in _COLOR_NAMES:
        dist = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
        if dist < best_dist:
            best_dist = dist
            best_name = name
    return best_name


__all__ = [
    "ColorInfo",
    "ImageData",
    "ImageFormat",
    "ImageProcessor",
    "ResizeMode",
    "ResizeResult",
]
