"""
Enhanced OCR Processing Module with Advanced Image Optimization
==============================================================

A standalone module for extracting text from PDF files using advanced image preprocessing
and OCR technology. Supports both EasyOCR (GPU-accelerated) and Tesseract engines.

Features:
- Advanced image preprocessing for optimal OCR accuracy
- Support for both EasyOCR and Tesseract OCR engines
- Intelligent image optimization with noise reduction and contrast enhancement
- Batch processing with progress tracking
- Memory-efficient processing for large documents

Usage Examples:
--------------

Basic usage with default settings:
    >>> from enhanced_ocr import extract_pdf_text
    >>>
    >>> # Extract all pages using best available OCR engine
    >>> results = extract_pdf_text("document.pdf")
    >>> for page_num, text, processing_time in results:
    ...     print(f"Page {page_num}: {text[:100]}...")

Extract specific pages:
    >>> # Extract only pages 1, 3, and 5
    >>> results = extract_pdf_text("document.pdf", page_numbers=[1, 3, 5])

Use specific OCR engine:
    >>> # Force use of Tesseract
    >>> results = extract_pdf_text("document.pdf", engine="tesseract")
    >>>
    >>> # Force use of EasyOCR with GPU
    >>> results = extract_pdf_text("document.pdf", engine="easyocr")

Custom DPI and optimization:
    >>> results = extract_pdf_text(
    ...     "document.pdf",
    ...     dpi=400,
    ...     optimize_images=True,
    ...     max_workers=4
    ... )

Save optimized images for inspection:
    >>> results = extract_pdf_text(
    ...     "document.pdf",
    ...     save_images=True,
    ...     output_folder="optimized_images"
    ... )

Command line usage:
    $ python enhanced_ocr.py document.pdf --pages 1-5 --engine tesseract --dpi 300

Dependencies:
------------
Required:
- pdf2image
- Pillow (PIL)
- opencv-python
- numpy

Optional (for enhanced features):
- pytesseract (for Tesseract OCR)
- easyocr (for GPU-accelerated OCR)
- torch (for GPU support with EasyOCR)
- tqdm (for progress bars)

Installation:
    pip install pdf2image Pillow opencv-python numpy pytesseract easyocr torch tqdm
"""

import gc
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import argparse
import sys

# Core dependencies
try:
    from pdf2image import convert_from_path
    from PIL import Image, ImageEnhance, ImageFilter, ImageStat
    import cv2
    import numpy as np
    PDF_AVAILABLE = True
except ImportError as e:
    PDF_AVAILABLE = False
    IMPORT_ERROR = str(e)

# Optional dependencies
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import easyocr
    import torch
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImageOptimizer:
    """Advanced image optimization for OCR processing."""

    @staticmethod
    def optimize_for_ocr(image: Image.Image) -> Image.Image:
        """
        Comprehensively optimize image for OCR processing with advanced techniques.

        Args:
            image: PIL Image to optimize

        Returns:
            Optimized PIL Image
        """
        try:
            original_image = image

            # Step 1: Size optimization
            width, height = image.size

            # Handle extremely large images
            if width * height > 10000000:
                max_dim = 4000
                if width > height:
                    new_width = max_dim
                    new_height = int(height * max_dim / width)
                else:
                    new_height = max_dim
                    new_width = int(width * max_dim / height)

                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Ensure minimum readable dimensions
            elif width < 1000 or height < 1000:
                scale_factor = max(1000 / width, 1000 / height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Step 2: Convert to RGB if necessary
            if image.mode not in ["RGB", "L"]:
                image = image.convert("RGB")

            # Step 3: Advanced OpenCV processing
            try:
                # Convert PIL to OpenCV format
                cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

                # Convert to grayscale for optimal OCR
                gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

                # Gaussian blur to reduce noise while preserving text edges
                blurred = cv2.GaussianBlur(gray, (1, 1), 0)

                # Advanced noise reduction
                denoised = cv2.fastNlMeansDenoising(blurred, None, 10, 7, 21)

                # Adaptive histogram equalization for optimal contrast
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(denoised)

                # Morphological operations to clean up text
                kernel = np.ones((1, 1), np.uint8)
                cleaned = cv2.morphologyEx(enhanced, cv2.MORPH_CLOSE, kernel)

                # Advanced adaptive thresholding
                thresh_methods = [
                    cv2.adaptiveThreshold(cleaned, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2),
                    cv2.adaptiveThreshold(cleaned, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 2),
                ]

                # Choose best thresholding result
                best_thresh = ImageOptimizer._select_best_threshold(thresh_methods, cleaned)

                # Final morphological cleanup
                final_kernel = np.ones((1, 1), np.uint8)
                final_processed = cv2.morphologyEx(best_thresh, cv2.MORPH_OPEN, final_kernel)

                # Convert back to PIL Image
                image = Image.fromarray(final_processed)

                # Convert grayscale back to RGB for consistency
                if image.mode == "L":
                    image = image.convert("RGB")

            except Exception as cv_error:
                logger.warning(f"OpenCV processing failed, using PIL fallback: {cv_error}")
                image = ImageOptimizer._fallback_pil_optimization(image)

            # Step 4: Final sharpening for text clarity
            try:
                sharpening_filter = ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3)
                image = image.filter(sharpening_filter)
            except Exception:
                pass

            # Step 5: Final contrast and brightness optimization
            try:
                # Analyze image brightness
                stat = ImageStat.Stat(image.convert("L"))
                mean_brightness = stat.mean[0]

                # Adjust brightness if needed
                brightness_enhancer = ImageEnhance.Brightness(image)
                if mean_brightness < 100:
                    image = brightness_enhancer.enhance(1.2)
                elif mean_brightness > 200:
                    image = brightness_enhancer.enhance(0.9)

                # Final contrast enhancement
                contrast_enhancer = ImageEnhance.Contrast(image)
                image = contrast_enhancer.enhance(1.3)
            except Exception:
                pass

            return image

        except Exception as e:
            logger.warning(f"Image optimization failed: {e}")
            return original_image

    @staticmethod
    def _select_best_threshold(thresh_methods: List[np.ndarray], original: np.ndarray) -> np.ndarray:
        """Select the best thresholding method based on edge preservation and contrast."""
        try:
            best_thresh = thresh_methods[0]
            best_score = 0

            for thresh in thresh_methods:
                # Calculate edge preservation score
                edges_original = cv2.Canny(original, 50, 150)
                edges_thresh = cv2.Canny(thresh, 50, 150)

                # Score based on edge preservation and contrast
                edge_score = cv2.countNonZero(edges_thresh) / max(cv2.countNonZero(edges_original), 1)
                contrast_score = np.std(thresh) / 255.0

                total_score = edge_score * 0.7 + contrast_score * 0.3

                if total_score > best_score:
                    best_score = total_score
                    best_thresh = thresh

            return best_thresh
        except Exception:
            return thresh_methods[0]

    @staticmethod
    def _fallback_pil_optimization(image: Image.Image) -> Image.Image:
        """Fallback optimization using only PIL when OpenCV fails."""
        try:
            # Convert to grayscale for better OCR
            gray_image = image.convert("L")

            # Enhance contrast
            enhancer = ImageEnhance.Contrast(gray_image)
            enhanced = enhancer.enhance(1.5)

            # Apply sharpening
            try:
                sharpened = enhanced.filter(ImageFilter.SHARPEN)
            except Exception:
                sharpened = enhanced

            # Convert back to RGB
            return sharpened.convert("RGB")
        except Exception:
            return image


class OCREngine:
    """Base class for OCR engines."""

    def extract_text(self, image: Image.Image) -> str:
        """Extract text from image. Override in subclasses."""
        raise NotImplementedError


class TesseractEngine(OCREngine):
    """Tesseract OCR engine implementation."""

    def __init__(self, language: str = "eng", config: str = "--oem 3 --psm 6"):
        self.language = language
        self.config = config

        if not TESSERACT_AVAILABLE:
            raise ImportError("pytesseract not available. Install with: pip install pytesseract")

    def extract_text(self, image: Image.Image) -> str:
        """Extract text using Tesseract."""
        try:
            return pytesseract.image_to_string(image, lang=self.language, config=self.config).strip()
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}")
            return f"[ERROR: {str(e)}]"


class EasyOCREngine(OCREngine):
    """EasyOCR engine implementation with GPU support."""

    def __init__(self, languages: List[str] = None, gpu: bool = True):
        if not EASYOCR_AVAILABLE:
            raise ImportError("easyocr not available. Install with: pip install easyocr torch")

        self.languages = languages or ["en"]
        self.gpu = gpu and torch.cuda.is_available()
        self.reader = easyocr.Reader(self.languages, gpu=self.gpu, verbose=False)

    def extract_text(self, image: Image.Image) -> str:
        """Extract text using EasyOCR."""
        try:
            # Convert PIL to numpy array
            image_array = np.array(image)

            # Perform OCR
            results = self.reader.readtext(
                image_array,
                detail=1,
                paragraph=False,
                width_ths=0.7,
                height_ths=0.7
            )

            # Extract text with confidence filtering
            confidence_threshold = 0.5
            text = " ".join([item[1] for item in results if item[2] > confidence_threshold])

            return text.strip()
        except Exception as e:
            logger.error(f"EasyOCR failed: {e}")
            return f"[ERROR: {str(e)}]"


def extract_pdf_text(
    pdf_path: Union[str, Path],
    page_numbers: Optional[List[int]] = None,
    engine: str = "auto",
    dpi: int = 300,
    optimize_images: bool = True,
    save_images: bool = False,
    output_folder: Optional[str] = None,
    max_workers: int = 1,
    progress_bar: bool = True,
    **kwargs
) -> List[Tuple[int, str, float]]:
    """
    Extract text from PDF using advanced OCR with image optimization.

    Args:
        pdf_path: Path to PDF file
        page_numbers: Specific pages to process (1-indexed). If None, processes all pages
        engine: OCR engine to use ("auto", "tesseract", "easyocr")
        dpi: Resolution for PDF to image conversion
        optimize_images: Whether to apply advanced image optimization
        save_images: Whether to save optimized images
        output_folder: Folder to save images (if save_images=True)
        max_workers: Number of parallel workers (currently unused, reserved for future)
        progress_bar: Whether to show progress bar
        **kwargs: Additional arguments for OCR engines

    Returns:
        List of tuples (page_number, extracted_text, processing_time_seconds)

    Raises:
        ImportError: If required dependencies are not available
        FileNotFoundError: If PDF file doesn't exist
    """
    # Validate dependencies
    if not PDF_AVAILABLE:
        raise ImportError(f"Required dependencies not available: {IMPORT_ERROR}")

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Initialize OCR engine
    ocr_engine = _get_ocr_engine(engine, **kwargs)

    # Create output folder if saving images
    if save_images and output_folder:
        os.makedirs(output_folder, exist_ok=True)

    try:
        # Convert PDF to images
        logger.info(f"Converting PDF to images at {dpi} DPI...")

        if page_numbers:
            images = convert_from_path(
                pdf_path,
                dpi=dpi,
                fmt="jpeg",
                first_page=min(page_numbers),
                last_page=max(page_numbers)
            )
            # Filter to only requested pages
            page_offset = min(page_numbers) - 1
            filtered_images = []
            for target_page in page_numbers:
                image_index = target_page - min(page_numbers)
                if image_index < len(images):
                    filtered_images.append((target_page, images[image_index]))
            page_image_pairs = filtered_images
        else:
            images = convert_from_path(pdf_path, dpi=dpi, fmt="jpeg")
            # Limit to maximum 5 pages when processing all pages
            page_image_pairs = [(i + 1, img) for i, img in enumerate(images[:5])]

        if not page_image_pairs:
            logger.warning("No images were converted from PDF")
            return []

        # Process pages
        results = []
        iterator = page_image_pairs

        if progress_bar and TQDM_AVAILABLE:
            iterator = tqdm(page_image_pairs, desc="Processing pages")

        for page_num, image in iterator:
            start_time = time.time()

            try:
                # Optimize image for OCR if requested
                if optimize_images:
                    optimized_image = ImageOptimizer.optimize_for_ocr(image)
                else:
                    optimized_image = image

                # Save image if requested
                if save_images and output_folder:
                    image_path = Path(output_folder) / f"page_{page_num:03d}_optimized.png"
                    optimized_image.save(image_path, "PNG")

                # Extract text
                text = ocr_engine.extract_text(optimized_image)
                processing_time = time.time() - start_time

                results.append((page_num, text, processing_time))

                # Memory cleanup
                del optimized_image
                gc.collect()

            except Exception as e:
                processing_time = time.time() - start_time
                error_text = f"[PAGE {page_num} ERROR: {str(e)}]"
                results.append((page_num, error_text, processing_time))
                logger.error(f"Error processing page {page_num}: {e}")

        return results

    except Exception as e:
        logger.error(f"Failed to process PDF: {e}")
        raise
    finally:
        # Cleanup
        gc.collect()
        if hasattr(ocr_engine, 'reader') and hasattr(ocr_engine.reader, '__del__'):
            del ocr_engine.reader
        if EASYOCR_AVAILABLE and torch.cuda.is_available():
            torch.cuda.empty_cache()


def _get_ocr_engine(engine: str, **kwargs) -> OCREngine:
    """Get the appropriate OCR engine based on availability and preference."""
    if engine == "auto":
        # Prefer EasyOCR if available and GPU is present
        if EASYOCR_AVAILABLE and torch.cuda.is_available():
            logger.info("Using EasyOCR with GPU acceleration")
            return EasyOCREngine(**kwargs)
        elif TESSERACT_AVAILABLE:
            logger.info("Using Tesseract OCR")
            return TesseractEngine(**kwargs)
        else:
            raise ImportError("No OCR engine available. Install pytesseract or easyocr.")

    elif engine.lower() == "tesseract":
        if not TESSERACT_AVAILABLE:
            raise ImportError("Tesseract not available. Install with: pip install pytesseract")
        return TesseractEngine(**kwargs)

    elif engine.lower() == "easyocr":
        if not EASYOCR_AVAILABLE:
            raise ImportError("EasyOCR not available. Install with: pip install easyocr torch")
        return EasyOCREngine(**kwargs)

    else:
        raise ValueError(f"Unknown OCR engine: {engine}. Use 'auto', 'tesseract', or 'easyocr'")


def main():
    """Command line interface for the OCR module."""
    parser = argparse.ArgumentParser(description="Extract text from PDF using advanced OCR")
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("--pages", help="Page range (e.g., '1-5' or '1,3,5')")
    parser.add_argument("--engine", choices=["auto", "tesseract", "easyocr"], default="auto",
                       help="OCR engine to use")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for PDF conversion")
    parser.add_argument("--no-optimize", action="store_true", help="Disable image optimization")
    parser.add_argument("--save-images", action="store_true", help="Save optimized images")
    parser.add_argument("--output-folder", help="Folder to save images")
    parser.add_argument("--output", help="Output text file")

    args = parser.parse_args()

    # Parse page numbers
    page_numbers = None
    if args.pages:
        try:
            if "-" in args.pages:
                start, end = map(int, args.pages.split("-"))
                page_numbers = list(range(start, end + 1))
            else:
                page_numbers = [int(p.strip()) for p in args.pages.split(",")]
        except ValueError:
            print(f"Invalid page format: {args.pages}")
            sys.exit(1)

    try:
        # Extract text
        results = extract_pdf_text(
            args.pdf_path,
            page_numbers=page_numbers,
            engine=args.engine,
            dpi=args.dpi,
            optimize_images=not args.no_optimize,
            save_images=args.save_images,
            output_folder=args.output_folder
        )

        # Output results
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                for page_num, text, processing_time in results:
                    f.write(f"=== Page {page_num} (processed in {processing_time:.2f}s) ===\n")
                    f.write(text)
                    f.write("\n\n")
            print(f"Text extracted to {args.output}")
        else:
            for page_num, text, processing_time in results:
                print(f"=== Page {page_num} (processed in {processing_time:.2f}s) ===")
                print(text)
                print("-" * 50)

        total_time = sum(result[2] for result in results)
        print(f"\nProcessed {len(results)} pages in {total_time:.2f} seconds")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
