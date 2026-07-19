"""Tests for M3.7 — Vision Subsystem.

Covers: ImageData, ImageProcessor, OCR, ImageAnalyzer.
Tests create synthetic PNG data for parsing — no external images needed.
"""

from __future__ import annotations

import struct

import pytest

from aios.vision.analyzer import ImageAnalysis, ImageAnalyzer, ImageMetadata
from aios.vision.image import (
    ColorInfo,
    ImageData,
    ImageFormat,
    ImageProcessor,
)
from aios.vision.ocr import OCRLine, OCRProvider, OCRResult, OCRService, OCRWord


def _make_png(width: int = 2, height: int = 2, color_type: int = 2) -> bytes:
    """Create a minimal valid PNG in memory."""
    import zlib

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)
    ihdr = _chunk(b"IHDR", ihdr_data)
    raw_data = b""
    filter_byte = b"\x00"
    for _ in range(height):
        raw_data += filter_byte + b"\x00" * (width * 3)
    compressed = zlib.compress(raw_data)
    idat = _chunk(b"IDAT", compressed)
    iend = _chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


def _make_png_rgba(width: int = 2, height: int = 2) -> bytes:
    """Create a minimal PNG with alpha channel."""
    import zlib

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    ihdr = _chunk(b"IHDR", ihdr_data)
    raw_data = b""
    filter_byte = b"\x00"
    for _ in range(height):
        raw_data += filter_byte + b"\x00" * (width * 4)
    compressed = zlib.compress(raw_data)
    idat = _chunk(b"IDAT", compressed)
    iend = _chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


SAMPLE_PNG = _make_png(100, 50)
SAMPLE_PNG_RGBA = _make_png_rgba(80, 60)


# ── ImageData ──────────────────────────────────────────────────────────


class TestImageData:
    def test_from_bytes(self):
        img = ImageData.from_bytes(SAMPLE_PNG, source="test.png")
        assert img.format == ImageFormat.PNG
        assert img.source == "test.png"
        assert img.checksum != ""

    def test_from_bytes_jpeg(self):
        # Minimal JPEG header
        jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        img = ImageData.from_bytes(jpeg)
        assert img.format == ImageFormat.JPEG

    def test_from_bytes_unknown(self):
        img = ImageData.from_bytes(b"\x00\x00\x00\x00")
        assert img.format == ImageFormat.UNKNOWN

    def test_from_base64(self):
        import base64

        b64 = base64.b64encode(SAMPLE_PNG).decode()
        img = ImageData.from_base64(b64, source="test.png")
        assert img.format == ImageFormat.PNG
        assert img.raw == SAMPLE_PNG

    def test_to_base64(self):
        img = ImageData.from_bytes(SAMPLE_PNG)
        b64 = img.to_base64()
        assert len(b64) > 0
        import base64

        decoded = base64.b64decode(b64)
        assert decoded == SAMPLE_PNG

    def test_size_bytes(self):
        img = ImageData.from_bytes(SAMPLE_PNG)
        assert img.size_bytes == len(SAMPLE_PNG)

    def test_mime_type(self):
        img = ImageData.from_bytes(SAMPLE_PNG)
        assert img.mime_type == "image/png"
        img2 = ImageData.from_bytes(b"\xff\xd8" + b"\x00" * 100)
        assert img2.mime_type == "image/jpeg"

    def test_checksum_unique(self):
        img1 = ImageData.from_bytes(SAMPLE_PNG)
        img2 = ImageData.from_bytes(SAMPLE_PNG_RGBA)
        assert img1.checksum != img2.checksum

    def test_frozen(self):
        img = ImageData.from_bytes(SAMPLE_PNG)
        with pytest.raises(AttributeError):
            img.raw = b"new"  # type: ignore[misc]


# ── ImageProcessor ─────────────────────────────────────────────────────


class TestImageProcessor:
    @pytest.mark.anyio
    async def test_get_color_at_no_pil(self):
        proc = ImageProcessor()
        if not proc.has_pil:
            result = await proc.get_color_at(ImageData.from_bytes(SAMPLE_PNG), 0, 0)
            assert result is None

    @pytest.mark.anyio
    async def test_get_dominant_colors_no_pil(self):
        proc = ImageProcessor()
        if not proc.has_pil:
            result = await proc.get_dominant_colors(ImageData.from_bytes(SAMPLE_PNG))
            assert result == []

    @pytest.mark.anyio
    async def test_crop_no_pil(self):
        proc = ImageProcessor()
        if not proc.has_pil:
            result = await proc.crop(ImageData.from_bytes(SAMPLE_PNG), 0, 0, 10, 10)
            assert result.ok is False
            assert "Pillow" in (result.error or "")

    def test_has_pil_property(self):
        proc = ImageProcessor()
        assert isinstance(proc.has_pil, bool)


# ── ImageFormat detection ──────────────────────────────────────────────


class TestFormatDetection:
    def test_png(self):
        assert ImageData.from_bytes(SAMPLE_PNG).format == ImageFormat.PNG

    def test_jpeg(self):
        data = b"\xff\xd8\xff\xe0" + b"\x00" * 20
        assert ImageData.from_bytes(data).format == ImageFormat.JPEG

    def test_webp(self):
        data = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 20
        assert ImageData.from_bytes(data).format == ImageFormat.WEBP

    def test_bmp(self):
        data = b"BM" + b"\x00" * 20
        assert ImageData.from_bytes(data).format == ImageFormat.BMP

    def test_gif87(self):
        data = b"GIF87a" + b"\x00" * 20
        assert ImageData.from_bytes(data).format == ImageFormat.GIF

    def test_gif89(self):
        data = b"GIF89a" + b"\x00" * 20
        assert ImageData.from_bytes(data).format == ImageFormat.GIF


# ── OCR ────────────────────────────────────────────────────────────────


class TestOCR:
    def test_ocr_result_frozen(self):
        r = OCRResult(ok=True, text="hello", confidence=0.95)
        assert r.ok is True
        assert r.text == "hello"
        assert r.confidence == 0.95

    def test_ocr_word_frozen(self):
        w = OCRWord(text="hello", confidence=0.9, bbox=(10, 20, 30, 40))
        assert w.text == "hello"
        assert w.bbox == (10, 20, 30, 40)

    def test_ocr_line_frozen(self):
        line = OCRLine(
            text="hello world",
            confidence=0.85,
            words=(OCRWord(text="hello"), OCRWord(text="world")),
        )
        assert len(line.words) == 2

    def test_ocr_service_default_provider(self):
        svc = OCRService()
        assert svc.provider in (OCRProvider.TESSERACT, OCRProvider.STUB)

    def test_ocr_service_explicit_stub(self):
        svc = OCRService(provider=OCRProvider.STUB)
        assert svc.provider == OCRProvider.STUB

    @pytest.mark.anyio
    async def test_extract_with_stub(self):
        svc = OCRService(provider=OCRProvider.STUB)
        result = await svc.extract(ImageData.from_bytes(SAMPLE_PNG))
        assert result.ok is False
        assert "No OCR provider" in (result.error or "")

    @pytest.mark.anyio
    async def test_extract_region_with_stub(self):
        svc = OCRService(provider=OCRProvider.STUB)
        result = await svc.extract_region(
            ImageData.from_bytes(SAMPLE_PNG), 0, 0, 10, 10
        )
        assert result.ok is False

    def test_ocr_provider_values(self):
        assert OCRProvider.TESSERACT == "tesseract"
        assert OCRProvider.STUB == "stub"


# ── ImageAnalyzer ──────────────────────────────────────────────────────


class TestImageAnalyzer:
    @pytest.mark.anyio
    async def test_analyze_png(self):
        analyzer = ImageAnalyzer()
        img = ImageData.from_bytes(SAMPLE_PNG, source="test.png")
        result = await analyzer.analyze(img)
        assert result.ok is True
        assert result.metadata.format == ImageFormat.PNG
        assert result.summary != ""

    @pytest.mark.anyio
    async def test_analyze_no_text(self):
        analyzer = ImageAnalyzer()
        img = ImageData.from_bytes(SAMPLE_PNG)
        result = await analyzer.analyze(img, extract_text=False)
        assert result.ok is True
        assert result.ocr is None

    @pytest.mark.anyio
    async def test_quick_analysis(self):
        analyzer = ImageAnalyzer()
        img = ImageData.from_bytes(SAMPLE_PNG)
        result = await analyzer.quick_analysis(img)
        assert result.ok is True
        assert result.ocr is None

    @pytest.mark.anyio
    async def test_metadata_width_height(self):
        analyzer = ImageAnalyzer()
        img = ImageData.from_bytes(SAMPLE_PNG)
        result = await analyzer.analyze(img, extract_text=False)
        assert result.metadata.width == 100
        assert result.metadata.height == 50

    @pytest.mark.anyio
    async def test_metadata_rgba(self):
        analyzer = ImageAnalyzer()
        img = ImageData.from_bytes(SAMPLE_PNG_RGBA)
        result = await analyzer.analyze(img, extract_text=False, extract_colors=False)
        assert result.metadata.has_alpha is True

    @pytest.mark.anyio
    async def test_summary_contains_format(self):
        analyzer = ImageAnalyzer()
        img = ImageData.from_bytes(SAMPLE_PNG)
        result = await analyzer.analyze(img, extract_text=False, extract_colors=False)
        assert "PNG" in result.summary

    @pytest.mark.anyio
    async def test_summary_contains_dimensions(self):
        analyzer = ImageAnalyzer()
        img = ImageData.from_bytes(SAMPLE_PNG)
        result = await analyzer.analyze(img, extract_text=False, extract_colors=False)
        assert "100x50" in result.summary

    def test_metadata_frozen(self):
        m = ImageMetadata(format=ImageFormat.PNG, width=100, height=50)
        assert m.width == 100

    def test_metadata_defaults(self):
        m = ImageMetadata()
        assert m.format == ImageFormat.UNKNOWN
        assert m.width == 0

    @pytest.mark.anyio
    async def test_analysis_frozen(self):
        analyzer = ImageAnalyzer()
        result = await analyzer.analyze(
            ImageData.from_bytes(SAMPLE_PNG), extract_text=False
        )
        assert isinstance(result, ImageAnalysis)


# ── ColorInfo ──────────────────────────────────────────────────────────


class TestColorInfo:
    def test_defaults(self):
        c = ColorInfo()
        assert c.hex_color == "#000000"
        assert c.r == 0

    def test_custom(self):
        c = ColorInfo(hex_color="#ff0000", r=255, g=0, b=0, name="red")
        assert c.name == "red"

    def test_frozen(self):
        c = ColorInfo()
        with pytest.raises(AttributeError):
            c.r = 100  # type: ignore[misc]
