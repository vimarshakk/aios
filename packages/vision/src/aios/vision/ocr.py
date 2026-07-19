"""OCR — extract text from images.

Provides OCRResult and OCRService. Uses pytesseract if available,
otherwise provides a stub that returns empty results. Designed to
be extended with cloud OCR providers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from aios.vision.image import ImageData


class OCRProvider(StrEnum):
    """OCR provider type."""

    TESSERACT = "tesseract"
    STUB = "stub"


@dataclass(frozen=True)
class OCRWord:
    """A single recognized word.

    Attributes:
        text: The recognized text.
        confidence: Confidence score (0.0 - 1.0).
        bbox: Bounding box (x, y, w, h) of the word.
    """

    text: str
    confidence: float = 0.0
    bbox: tuple[int, int, int, int] = (0, 0, 0, 0)


@dataclass(frozen=True)
class OCRLine:
    """A line of recognized text.

    Attributes:
        text: The full line text.
        confidence: Average confidence.
        words: Individual words in this line.
    """

    text: str
    confidence: float = 0.0
    words: tuple[OCRWord, ...] = ()


@dataclass(frozen=True)
class OCRResult:
    """OCR extraction result.

    Attributes:
        ok: Whether OCR succeeded.
        text: Full extracted text.
        lines: Structured line-by-line results.
        confidence: Overall confidence score.
        provider: Which OCR provider was used.
        error: Error message if failed.
    """

    ok: bool
    text: str = ""
    lines: tuple[OCRLine, ...] = ()
    confidence: float = 0.0
    provider: OCRProvider = OCRProvider.STUB
    error: str | None = None


class OCRService:
    """OCR service with provider abstraction.

    Usage::

        svc = OCRService()
        result = await svc.extract(image)
        print(result.text)
    """

    def __init__(self, provider: OCRProvider | None = None) -> None:
        if provider is None:
            self._provider = (
                OCRProvider.TESSERACT if _has_tesseract() else OCRProvider.STUB
            )
        else:
            self._provider = provider

    @property
    def provider(self) -> OCRProvider:
        """Current OCR provider."""
        return self._provider

    async def extract(
        self,
        image: ImageData,
        lang: str = "eng",
    ) -> OCRResult:
        """Extract text from an image.

        Args:
            image: Image to process.
            lang: Language for OCR (default: English).

        Returns:
            OCRResult with extracted text and confidence.
        """
        if self._provider == OCRProvider.TESSERACT:
            return await self._extract_tesseract(image, lang)
        return OCRResult(ok=False, error="No OCR provider available (install pytesseract)")

    async def extract_region(
        self,
        image: ImageData,
        x: int,
        y: int,
        w: int,
        h: int,
        lang: str = "eng",
    ) -> OCRResult:
        """Extract text from a specific region. Requires PIL for cropping."""
        try:
            import io

            from PIL import Image as PILImage

            pil_img = PILImage.open(io.BytesIO(image.raw))
            cropped = pil_img.crop((x, y, x + w, y + h))
            buf = io.BytesIO()
            cropped.save(buf, format="PNG")
            cropped_img = ImageData.from_bytes(buf.getvalue())
            return await self.extract(cropped_img, lang)
        except ImportError:
            return OCRResult(ok=False, error="Pillow required for region extraction")
        except Exception as exc:
            return OCRResult(ok=False, error=str(exc))

    async def _extract_tesseract(
        self, image: ImageData, lang: str
    ) -> OCRResult:
        """Extract using pytesseract."""
        try:
            import io

            import pytesseract
            from PIL import Image as PILImage

            pil_img = PILImage.open(io.BytesIO(image.raw))
            # Get full text
            text = pytesseract.image_to_string(pil_img, lang=lang)
            # Get detailed data
            data = pytesseract.image_to_data(
                pil_img, lang=lang, output_type=pytesseract.Output.DICT
            )
            lines = _parse_tesseract_data(data)
            avg_conf = _average_confidence(data)
            return OCRResult(
                ok=True,
                text=text.strip(),
                lines=tuple(lines),
                confidence=avg_conf,
                provider=OCRProvider.TESSERACT,
            )
        except ImportError:
            return OCRResult(ok=False, error="pytesseract not installed")
        except Exception as exc:
            return OCRResult(ok=False, error=str(exc))


def _has_tesseract() -> bool:
    try:
        import pytesseract  # noqa: F401

        return True
    except ImportError:
        return False


def _parse_tesseract_data(data: dict) -> list[OCRLine]:
    """Parse tesseract output dict into OCRLines."""
    lines: dict[int, list[OCRWord]] = {}
    n = len(data.get("text", []))
    for i in range(n):
        text = data["text"][i].strip()
        conf = float(data["conf"][i]) / 100.0 if data["conf"][i] != "-1" else 0.0
        line_num = data["line_num"][i]
        if text:
            word = OCRWord(
                text=text,
                confidence=conf,
                bbox=(
                    data["left"][i],
                    data["top"][i],
                    data["width"][i],
                    data["height"][i],
                ),
            )
            lines.setdefault(line_num, []).append(word)
    result = []
    for line_num in sorted(lines):
        words = lines[line_num]
        line_text = " ".join(w.text for w in words)
        avg_conf = sum(w.confidence for w in words) / len(words) if words else 0.0
        result.append(OCRLine(text=line_text, confidence=avg_conf, words=tuple(words)))
    return result


def _average_confidence(data: dict) -> float:
    confs = [
        float(c) / 100.0
        for c in data.get("conf", [])
        if c != "-1" and float(c) > 0
    ]
    return sum(confs) / len(confs) if confs else 0.0


__all__ = [
    "OCRLine",
    "OCRProvider",
    "OCRResult",
    "OCRService",
    "OCRWord",
]
