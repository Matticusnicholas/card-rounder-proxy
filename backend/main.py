"""
MTG Proxy Card Processor API

A FastAPI backend for processing MTG proxy card sheets:
- Detects card edges from uploaded images or PDFs
- Rounds corners to MTG specifications (3mm radius)
- Generates SVG cut files with Silhouette Portrait 4 registration marks
- Outputs print-ready PDFs with registration marks
"""

import io
import base64
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image
from typing import Optional

from card_processor import CardProcessor
from svg_generator import SilhouetteSVGGenerator
from pdf_handler import PDFHandler, PDFWithCutLines

app = FastAPI(
    title="MTG Proxy Card Processor",
    description="Process MTG proxy sheets for Silhouette Portrait 4 cutting",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MTG card specifications (in mm)
MTG_CARD_WIDTH_MM = 63.0
MTG_CARD_HEIGHT_MM = 88.0
MTG_CORNER_RADIUS_MM = 3.0

# Supported file types
SUPPORTED_IMAGE_TYPES = {'image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'image/bmp'}
SUPPORTED_PDF_TYPES = {'application/pdf'}
SUPPORTED_TYPES = SUPPORTED_IMAGE_TYPES | SUPPORTED_PDF_TYPES


def is_pdf(content_type: str) -> bool:
    """Check if the file is a PDF."""
    return content_type in SUPPORTED_PDF_TYPES


def is_image(content_type: str) -> bool:
    """Check if the file is an image."""
    return content_type in SUPPORTED_IMAGE_TYPES or content_type.startswith('image/')


async def load_image_from_upload(file: UploadFile, dpi: int = 300) -> tuple[Image.Image, bool, int]:
    """
    Load an image from an uploaded file (image or PDF).

    Returns:
        Tuple of (image, is_pdf, page_count)
    """
    contents = await file.read()
    content_type = file.content_type or ''

    if is_pdf(content_type):
        pdf_handler = PDFHandler(dpi=dpi)
        images = pdf_handler.read_pdf(contents)
        if not images:
            raise HTTPException(status_code=400, detail="Could not read PDF file")
        # Return first page for now (multi-page support in separate endpoint)
        return images[0], True, len(images)
    else:
        image = Image.open(io.BytesIO(contents))
        return image, False, 1


@app.get("/")
async def root():
    return {"message": "MTG Proxy Card Processor API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/api/process")
async def process_card_sheet(
    file: UploadFile = File(...),
    grid_cols: int = 3,
    grid_rows: int = 3,
    auto_detect: bool = True,
    dpi: int = 300,
    page_size: str = Query("letter", regex="^(letter|a4)$"),
    page: int = 1
):
    """
    Process an uploaded card sheet image or PDF.

    Args:
        file: The uploaded image or PDF file
        grid_cols: Expected number of columns (default 3)
        grid_rows: Expected number of rows (default 3)
        auto_detect: Whether to auto-detect card edges (default True)
        dpi: Print DPI for proper sizing (default 300)
        page_size: Output PDF page size ('letter' or 'a4')
        page: Page number to process for multi-page PDFs (1-indexed)

    Returns:
        JSON with processed image, SVG cut file, and PDF
    """
    content_type = file.content_type or ''

    # Validate file type
    if not (is_image(content_type) or is_pdf(content_type)):
        raise HTTPException(
            status_code=400,
            detail="File must be an image (PNG, JPEG, WebP) or PDF"
        )

    try:
        # Read file contents
        contents = await file.read()
        is_pdf_file = is_pdf(content_type)
        page_count = 1

        if is_pdf_file:
            pdf_handler = PDFHandler(dpi=dpi)
            images = pdf_handler.read_pdf(contents)
            if not images:
                raise HTTPException(status_code=400, detail="Could not read PDF file")
            page_count = len(images)
            if page < 1 or page > page_count:
                raise HTTPException(
                    status_code=400,
                    detail=f"Page {page} not found. PDF has {page_count} page(s)."
                )
            image = images[page - 1]
        else:
            image = Image.open(io.BytesIO(contents))

        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'P'):
            image = image.convert('RGB')

        # Initialize processor
        processor = CardProcessor(
            card_width_mm=MTG_CARD_WIDTH_MM,
            card_height_mm=MTG_CARD_HEIGHT_MM,
            corner_radius_mm=MTG_CORNER_RADIUS_MM,
            dpi=dpi
        )

        # Detect cards
        if auto_detect:
            cards = processor.detect_cards(image)
        else:
            cards = processor.generate_grid(image, grid_cols, grid_rows)

        if not cards:
            raise HTTPException(
                status_code=400,
                detail="No cards detected. Try adjusting the grid settings or image quality."
            )

        # Round corners on the image
        processed_image = processor.round_corners(image, cards)

        # Generate SVG cut file
        svg_generator = SilhouetteSVGGenerator(
            image_width_mm=image.width / dpi * 25.4,
            image_height_mm=image.height / dpi * 25.4,
            corner_radius_mm=MTG_CORNER_RADIUS_MM,
            dpi=dpi
        )
        svg_content = svg_generator.generate(cards, image.width, image.height)

        # Generate print-ready PDF
        pdf_generator = PDFWithCutLines(dpi=dpi)
        pdf_bytes = pdf_generator.create_combined_pdf(
            image=processed_image,
            cards=cards,
            corner_radius_mm=MTG_CORNER_RADIUS_MM,
            page_size=page_size,
            show_cut_lines=False  # Clean print version
        )
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

        # Convert processed image to base64 PNG
        img_buffer = io.BytesIO()
        processed_image.save(img_buffer, format='PNG', dpi=(dpi, dpi))
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')

        # Prepare card data for frontend
        cards_data = [
            {
                "id": i,
                "x": card["x"],
                "y": card["y"],
                "width": card["width"],
                "height": card["height"]
            }
            for i, card in enumerate(cards)
        ]

        return JSONResponse({
            "success": True,
            "cards_detected": len(cards),
            "cards": cards_data,
            "processed_image": f"data:image/png;base64,{img_base64}",
            "svg_cut_file": svg_content,
            "pdf_print_file": f"data:application/pdf;base64,{pdf_base64}",
            "image_dimensions": {
                "width_px": image.width,
                "height_px": image.height,
                "width_mm": image.width / dpi * 25.4,
                "height_mm": image.height / dpi * 25.4
            },
            "source_info": {
                "is_pdf": is_pdf_file,
                "page_count": page_count,
                "current_page": page
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.post("/api/preview")
async def preview_detection(
    file: UploadFile = File(...),
    grid_cols: int = 3,
    grid_rows: int = 3,
    auto_detect: bool = True,
    dpi: int = 300,
    page: int = 1
):
    """
    Preview card detection without full processing.
    Returns the original image with detected card boundaries overlaid.
    Supports both images and PDFs.
    """
    content_type = file.content_type or ''

    if not (is_image(content_type) or is_pdf(content_type)):
        raise HTTPException(
            status_code=400,
            detail="File must be an image (PNG, JPEG, WebP) or PDF"
        )

    try:
        contents = await file.read()
        is_pdf_file = is_pdf(content_type)
        page_count = 1

        if is_pdf_file:
            pdf_handler = PDFHandler(dpi=dpi)
            images = pdf_handler.read_pdf(contents)
            if not images:
                raise HTTPException(status_code=400, detail="Could not read PDF file")
            page_count = len(images)
            if page < 1 or page > page_count:
                raise HTTPException(
                    status_code=400,
                    detail=f"Page {page} not found. PDF has {page_count} page(s)."
                )
            image = images[page - 1]
        else:
            image = Image.open(io.BytesIO(contents))

        if image.mode in ('RGBA', 'P'):
            image = image.convert('RGB')

        processor = CardProcessor(
            card_width_mm=MTG_CARD_WIDTH_MM,
            card_height_mm=MTG_CARD_HEIGHT_MM,
            corner_radius_mm=MTG_CORNER_RADIUS_MM,
            dpi=dpi
        )

        if auto_detect:
            cards = processor.detect_cards(image)
        else:
            cards = processor.generate_grid(image, grid_cols, grid_rows)

        # Create preview with detected boundaries
        preview_image = processor.create_detection_preview(image, cards)

        img_buffer = io.BytesIO()
        preview_image.save(img_buffer, format='PNG')
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')

        cards_data = [
            {
                "id": i,
                "x": card["x"],
                "y": card["y"],
                "width": card["width"],
                "height": card["height"]
            }
            for i, card in enumerate(cards)
        ]

        return JSONResponse({
            "success": True,
            "cards_detected": len(cards),
            "cards": cards_data,
            "preview_image": f"data:image/png;base64,{img_base64}",
            "source_info": {
                "is_pdf": is_pdf_file,
                "page_count": page_count,
                "current_page": page
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview error: {str(e)}")


@app.post("/api/pdf-info")
async def get_pdf_info(file: UploadFile = File(...)):
    """
    Get information about an uploaded PDF file.
    Returns page count and dimensions for each page.
    """
    if not is_pdf(file.content_type or ''):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    try:
        contents = await file.read()
        pdf_handler = PDFHandler()
        info = pdf_handler.get_pdf_info(contents)
        return JSONResponse(info)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading PDF: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
