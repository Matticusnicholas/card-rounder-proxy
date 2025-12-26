"""
PDF Handler Module

Handles PDF input/output for MTG proxy card processing.
"""

import io
import fitz  # PyMuPDF
from PIL import Image
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from typing import List


class PDFHandler:
    """Handles PDF reading and writing for card processing."""

    PAGE_SIZES = {
        'letter': letter,
        'a4': A4,
    }

    def __init__(self, dpi: int = 300):
        self.dpi = dpi

    def read_pdf(self, pdf_bytes: bytes) -> List[Image.Image]:
        """Read a PDF and convert each page to a PIL Image."""
        images = []
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            zoom = self.dpi / 72
            matrix = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)

        doc.close()
        return images

    def get_pdf_info(self, pdf_bytes: bytes) -> dict:
        """Get information about a PDF file."""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        info = {"page_count": len(doc), "pages": []}

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            rect = page.rect
            info["pages"].append({
                "page": page_num + 1,
                "width_pt": rect.width,
                "height_pt": rect.height,
                "width_mm": rect.width * 25.4 / 72,
                "height_mm": rect.height * 25.4 / 72
            })

        doc.close()
        return info


class PDFWithCutLines:
    """Generate a PDF for print-and-cut workflow."""

    def __init__(self, dpi: int = 300):
        self.dpi = dpi

    def create_combined_pdf(
        self,
        image: Image.Image,
        cards: List[dict],
        corner_radius_mm: float = 3.0,
        page_size: str = 'letter',
        show_cut_lines: bool = False
    ) -> bytes:
        """
        Create a PDF with the processed image positioned at top-left.
        This ensures SVG cut lines will align correctly.
        """
        buffer = io.BytesIO()
        page_dimensions = PDFHandler.PAGE_SIZES.get(page_size, letter)

        c = canvas.Canvas(buffer, pagesize=page_dimensions)
        page_width, page_height = page_dimensions

        # Image dimensions in points
        img_width_pt = image.width * 72 / self.dpi
        img_height_pt = image.height * 72 / self.dpi

        # Position image at top-left (PDF origin is bottom-left, so we need to flip Y)
        # Image top-left at (0, page_height - img_height)
        x_offset = 0
        y_offset = page_height - img_height_pt

        # Draw the image
        img_reader = ImageReader(image)
        c.drawImage(
            img_reader,
            x_offset,
            y_offset,
            width=img_width_pt,
            height=img_height_pt
        )

        # Optionally draw cut lines (for preview)
        if show_cut_lines:
            self._draw_cut_lines(
                c, cards, x_offset, y_offset,
                img_width_pt, img_height_pt,
                image.width, image.height,
                corner_radius_mm
            )

        c.save()
        buffer.seek(0)
        return buffer.getvalue()

    def _draw_cut_lines(
        self,
        c: canvas,
        cards: List[dict],
        x_offset: float,
        y_offset: float,
        img_width_pt: float,
        img_height_pt: float,
        img_width_px: int,
        img_height_px: int,
        corner_radius_mm: float
    ):
        """Draw cut lines on the PDF (for preview)."""
        c.setStrokeColorRGB(1, 0, 0)
        c.setLineWidth(0.5)

        scale_x = img_width_pt / img_width_px
        scale_y = img_height_pt / img_height_px

        for card in cards:
            # Convert pixel coordinates to points
            # Note: PDF y-axis is from bottom, image y-axis is from top
            x = x_offset + card["x"] * scale_x
            y = y_offset + img_height_pt - (card["y"] + card["height"]) * scale_y
            w = card["width"] * scale_x
            h = card["height"] * scale_y

            card_scale = min(
                card["width"] / (63 * self.dpi / 25.4),
                card["height"] / (88 * self.dpi / 25.4)
            )
            radius = corner_radius_mm * mm * card_scale

            c.roundRect(x, y, w, h, radius, fill=0, stroke=1)
