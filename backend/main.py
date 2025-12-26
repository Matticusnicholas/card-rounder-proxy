"""
MTG Proxy Card Processor API

A FastAPI backend for processing MTG proxy card sheets:
- Detects card edges from uploaded images
- Rounds corners to MTG specifications (3mm radius)
- Generates SVG cut files with Silhouette Portrait 4 registration marks
"""

import io
import base64
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import numpy as np
from PIL import Image

from card_processor import CardProcessor
from svg_generator import SilhouetteSVGGenerator

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
    dpi: int = 300
):
    """
    Process an uploaded card sheet image.

    Args:
        file: The uploaded image file
        grid_cols: Expected number of columns (default 3)
        grid_rows: Expected number of rows (default 3)
        auto_detect: Whether to auto-detect card edges (default True)
        dpi: Print DPI for proper sizing (default 300)

    Returns:
        JSON with processed image (base64) and SVG cut file
    """

    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        # Read and process image
        contents = await file.read()
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

        # Convert processed image to base64
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
            "image_dimensions": {
                "width_px": image.width,
                "height_px": image.height,
                "width_mm": image.width / dpi * 25.4,
                "height_mm": image.height / dpi * 25.4
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
    dpi: int = 300
):
    """
    Preview card detection without full processing.
    Returns the original image with detected card boundaries overlaid.
    """

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        contents = await file.read()
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
            "preview_image": f"data:image/png;base64,{img_base64}"
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
