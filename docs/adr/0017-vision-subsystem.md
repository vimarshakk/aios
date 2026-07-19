# ADR-0017: Vision Subsystem

**Date:** 2025-07-17
**Status:** Accepted
**Deciders:** Core team

## Context

M3.7 added vision capabilities for image processing, OCR, and screenshot analysis. The subsystem enables agents to extract text and structure from images, perform basic image transformations, and analyze visual content.

## Decision

Three-layer architecture:

- **ImageProcessor:** Core image operations — format detection, resize, crop, metadata extraction. `ImageData` dataclass holds raw bytes + format. `ImageFormat` (PNG/JPEG/GIF/WEBP/BMP). `ResizeMode` (FIT, FILL, STRETCH). `ColorInfo` for dominant color analysis.
- **OCRService:** Text extraction from images. `OCRProvider` enum (TESSERACT, CLOUD). `OCRResult` with `OCRLine`, `OCRWord` structured output. Optional PIL dependency for cropping.
- **ImageAnalyzer:** Higher-level analysis — dimension extraction, format detection, metadata parsing (PNG/JPEG chunks). `ImageAnalysis` and `ImageMetadata` dataclasses.

## Consequences

- PIL is optional — only needed for resize/crop/OCR cropping
- Tesseract integration via `pytesseract` (optional dependency)
- Vision package depends only on `aios-core`
- Format detection is byte-signature based (magic numbers)
- PNG metadata parsing reads IHDR chunk; JPEG reads SOF markers
- OCR word-level data includes bounding boxes (if available)

## Key Design Decisions

1. **Lazy PIL import:** Users who only need format detection don't need PIL
2. **PIL-free metadata parsing:** PNG/JPEG headers readable without PIL
3. **OCR provider abstraction:** Tesseract now, cloud providers later
4. **StrEnum for enums:** `ImageFormat` and `OCRProvider` use `enum.StrEnum`

## Alternatives Considered

1. **OpenCV (cv2):** Powerful but heavy dependency
2. **Pillow only:** Good but we wanted format detection without PIL
3. **Cloud OCR only:** Adds network dependency, privacy concerns

## References

- `packages/vision/src/aios/vision/image.py`
- `packages/vision/src/aios/vision/ocr.py`
- `packages/vision/src/aios/vision/analyzer.py`
- `tests/test_vision.py`
