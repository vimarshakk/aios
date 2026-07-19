"""Image analyzer — analyze images for content, structure, and metadata.

Combines image processing, OCR, and metadata extraction into a
unified analysis interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aios.vision.image import ColorInfo, ImageData, ImageFormat, ImageProcessor
from aios.vision.ocr import OCRResult, OCRService


@dataclass(frozen=True)
class ImageMetadata:
    """Image metadata from file headers.

    Attributes:
        format: Detected image format.
        width: Width in pixels.
        height: Height in pixels.
        size_bytes: File size in bytes.
        has_alpha: Whether the image has an alpha channel.
        color_depth: Bits per pixel.
    """

    format: ImageFormat = ImageFormat.UNKNOWN
    width: int = 0
    height: int = 0
    size_bytes: int = 0
    has_alpha: bool = False
    color_depth: int = 0


@dataclass(frozen=True)
class ImageAnalysis:
    """Complete image analysis result.

    Attributes:
        ok: Whether analysis succeeded.
        metadata: Image metadata.
        ocr: OCR result (text extraction).
        dominant_colors: Top dominant colors.
        text_detected: Whether text was found in the image.
        summary: Human-readable summary.
        error: Error message if analysis failed.
    """

    ok: bool
    metadata: ImageMetadata = field(default_factory=ImageMetadata)
    ocr: OCRResult | None = None
    dominant_colors: tuple[ColorInfo, ...] = ()
    text_detected: bool = False
    summary: str = ""
    error: str | None = None


class ImageAnalyzer:
    """Unified image analysis.

    Combines metadata extraction, OCR, color analysis, and summarization.

    Usage::

        analyzer = ImageAnalyzer()
        img = ImageData.from_file("screenshot.png")
        result = await analyzer.analyze(img)
        print(result.summary)
    """

    def __init__(self) -> None:
        self._processor = ImageProcessor()
        self._ocr = OCRService()

    async def analyze(
        self,
        image: ImageData,
        *,
        extract_text: bool = True,
        extract_colors: bool = True,
        color_count: int = 5,
    ) -> ImageAnalysis:
        """Perform full image analysis.

        Args:
            image: Image to analyze.
            extract_text: Whether to run OCR.
            extract_colors: Whether to extract dominant colors.
            color_count: Number of dominant colors to extract.

        Returns:
            ImageAnalysis with all extracted information.
        """
        try:
            metadata = self._extract_metadata(image)
            ocr_result = None
            if extract_text:
                ocr_result = await self._ocr.extract(image)
            colors = ()
            if extract_colors:
                color_list = await self._processor.get_dominant_colors(image, color_count)
                colors = tuple(color_list)
            summary = self._build_summary(metadata, ocr_result, colors)
            return ImageAnalysis(
                ok=True,
                metadata=metadata,
                ocr=ocr_result,
                dominant_colors=colors,
                text_detected=bool(ocr_result and ocr_result.ok and ocr_result.text),
                summary=summary,
            )
        except Exception as exc:
            return ImageAnalysis(ok=False, error=str(exc))

    async def quick_analysis(self, image: ImageData) -> ImageAnalysis:
        """Fast analysis without OCR (metadata + colors only)."""
        return await self.analyze(image, extract_text=False)

    def _extract_metadata(self, image: ImageData) -> ImageMetadata:
        """Extract metadata from image bytes."""
        w, h = image.width, image.height
        has_alpha = False
        color_depth = 0
        if image.format == ImageFormat.PNG:
            w, h, has_alpha, color_depth = _parse_png_header(image.raw)
        elif image.format == ImageFormat.JPEG:
            w, h = _parse_jpeg_size(image.raw)
            color_depth = 24
        return ImageMetadata(
            format=image.format,
            width=w or image.width,
            height=h or image.height,
            size_bytes=image.size_bytes,
            has_alpha=has_alpha,
            color_depth=color_depth,
        )

    def _build_summary(
        self,
        metadata: ImageMetadata,
        ocr: OCRResult | None,
        colors: tuple[ColorInfo, ...],
    ) -> str:
        parts = []
        parts.append(
            f"{metadata.format.value.upper()} image, "
            f"{metadata.width}x{metadata.height}, "
            f"{metadata.size_bytes:,} bytes"
        )
        if ocr and ocr.ok and ocr.text:
            word_count = len(ocr.text.split())
            parts.append(f"Contains {word_count} words of text")
        if colors:
            color_str = ", ".join(c.name or c.hex_color for c in colors[:3])
            parts.append(f"Dominant colors: {color_str}")
        if metadata.has_alpha:
            parts.append("Has alpha channel")
        return ". ".join(parts) + "."


def _parse_png_header(data: bytes) -> tuple[int, int, bool, int]:
    """Parse PNG IHDR chunk for dimensions and color info."""
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return 0, 0, False, 0
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    bit_depth = data[24]
    color_type = data[25]
    has_alpha = color_type in (4, 6)
    color_depth = bit_depth * (4 if color_type in (4, 6) else 3 if color_type == 2 else 1)
    return width, height, has_alpha, color_depth


def _parse_jpeg_size(data: bytes) -> tuple[int, int]:
    """Parse JPEG SOF marker for dimensions."""
    i = 2
    while i < len(data) - 1:
        if data[i] != 0xFF:
            break
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            if i + 9 < len(data):
                h = int.from_bytes(data[i + 5 : i + 7], "big")
                w = int.from_bytes(data[i + 7 : i + 9], "big")
                return w, h
            break
        if marker == 0xD9:
            break
        if marker == 0xDA:
            break
        if 0xD0 <= marker <= 0xD9:
            i += 2
        else:
            if i + 3 < len(data):
                length = int.from_bytes(data[i + 2 : i + 4], "big")
                i += 2 + length
            else:
                break
    return 0, 0


__all__ = [
    "ImageAnalysis",
    "ImageAnalyzer",
    "ImageMetadata",
]
