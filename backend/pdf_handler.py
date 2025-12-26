"""
PDF Handler Module

Handles PDF input/output for MTG proxy card processing:
- Reading PDF pages and converting to images
- Generating print-ready PDFs with registration marks
"""

import io
import fitz  # PyMuPDF
from PIL import Image
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from typing import List, Tuple, Optional


class PDFHandler:
    """Handles PDF reading and writing for card processing."""

    # Supported page sizes
    PAGE_SIZES = {
        'letter': letter,  # 8.5" x 11" (215.9mm x 279.4mm)
        'a4': A4,  # 210mm x 297mm
    }

    def __init__(self, dpi: int = 300):
        """
        Initialize PDF handler.

        Args:
            dpi: Resolution for PDF to image conversion
        """
        self.dpi = dpi

    def read_pdf(self, pdf_bytes: bytes) -> List[Image.Image]:
        """
        Read a PDF and convert each page to a PIL Image.

        Args:
            pdf_bytes: Raw PDF file bytes

        Returns:
            List of PIL Images, one per page
        """
        images = []
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)

            # Calculate zoom for desired DPI (fitz default is 72 DPI)
            zoom = self.dpi / 72
            matrix = fitz.Matrix(zoom, zoom)

            # Render page to pixmap
            pix = page.get_pixmap(matrix=matrix)

            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)

        doc.close()
        return images

    def get_pdf_info(self, pdf_bytes: bytes) -> dict:
        """
        Get information about a PDF file.

        Args:
            pdf_bytes: Raw PDF file bytes

        Returns:
            Dictionary with PDF metadata
        """
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        info = {
            "page_count": len(doc),
            "pages": []
        }

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

    def create_print_pdf(
        self,
        images: List[Image.Image],
        cards_per_page: List[List[dict]],
        corner_radius_mm: float = 3.0,
        page_size: str = 'letter',
        include_reg_marks: bool = True,
        reg_mark_margin_mm: float = 10.0
    ) -> bytes:
        """
        Create a print-ready PDF with registration marks.

        Args:
            images: List of processed PIL Images (one per page)
            cards_per_page: List of card regions for each page
            corner_radius_mm: Corner radius for reference
            page_size: Page size ('letter' or 'a4')
            include_reg_marks: Whether to add Silhouette registration marks
            reg_mark_margin_mm: Margin for registration marks

        Returns:
            PDF file as bytes
        """
        buffer = io.BytesIO()
        page_dimensions = self.PAGE_SIZES.get(page_size, letter)

        c = canvas.Canvas(buffer, pagesize=page_dimensions)
        page_width, page_height = page_dimensions

        for i, image in enumerate(images):
            if i > 0:
                c.showPage()

            # Calculate image placement to center on page
            img_width_pt = image.width * 72 / self.dpi
            img_height_pt = image.height * 72 / self.dpi

            # Center the image
            x_offset = (page_width - img_width_pt) / 2
            y_offset = (page_height - img_height_pt) / 2

            # Draw the image
            img_reader = ImageReader(image)
            c.drawImage(
                img_reader,
                x_offset,
                y_offset,
                width=img_width_pt,
                height=img_height_pt
            )

            # Add registration marks if requested
            if include_reg_marks:
                self._add_registration_marks(
                    c, page_width, page_height, reg_mark_margin_mm
                )

        c.save()
        buffer.seek(0)
        return buffer.getvalue()

    def _add_registration_marks(
        self,
        c: canvas,
        page_width: float,
        page_height: float,
        margin_mm: float
    ):
        """
        Add Silhouette-compatible registration marks to the PDF.

        Args:
            c: ReportLab canvas
            page_width: Page width in points
            page_height: Page height in points
            margin_mm: Margin from edge in mm
        """
        margin = margin_mm * mm
        mark_size = 5 * mm
        line_width = 1 * mm

        c.setStrokeColorRGB(0, 0, 0)
        c.setFillColorRGB(0, 0, 0)
        c.setLineWidth(0.5)

        # Registration mark positions (3-point system for Silhouette)
        positions = [
            # Top-left
            (margin, page_height - margin),
            # Top-right
            (page_width - margin, page_height - margin),
            # Bottom-left
            (margin, margin),
        ]

        for x, y in positions:
            # Draw L-shaped mark
            # Horizontal line
            c.rect(x, y - line_width, mark_size, line_width, fill=1, stroke=0)
            # Vertical line
            c.rect(x, y - mark_size, line_width, mark_size, fill=1, stroke=0)

    def create_print_pdf_simple(
        self,
        image: Image.Image,
        page_size: str = 'letter',
        include_reg_marks: bool = True
    ) -> bytes:
        """
        Create a simple single-page print PDF.

        Args:
            image: Processed PIL Image
            page_size: Page size ('letter' or 'a4')
            include_reg_marks: Whether to add registration marks

        Returns:
            PDF file as bytes
        """
        return self.create_print_pdf(
            images=[image],
            cards_per_page=[[]],
            page_size=page_size,
            include_reg_marks=include_reg_marks
        )


class PDFWithCutLines:
    """Generate a PDF that includes both the print image and cut line overlay."""

    def __init__(self, dpi: int = 300):
        self.dpi = dpi

    def create_combined_pdf(
        self,
        image: Image.Image,
        cards: List[dict],
        corner_radius_mm: float = 3.0,
        page_size: str = 'letter',
        show_cut_lines: bool = False  # Usually False for actual printing
    ) -> bytes:
        """
        Create a PDF with the processed image and optional cut line overlay.

        For Silhouette workflow, you typically:
        1. Print this PDF (without cut lines visible)
        2. Import the SVG cut file separately into Silhouette Studio

        Args:
            image: Processed image with rounded corners
            cards: List of card regions
            corner_radius_mm: Corner radius
            page_size: Page size
            show_cut_lines: Whether to draw cut lines (for preview only)

        Returns:
            PDF file as bytes
        """
        buffer = io.BytesIO()
        page_dimensions = PDFHandler.PAGE_SIZES.get(page_size, letter)

        c = canvas.Canvas(buffer, pagesize=page_dimensions)
        page_width, page_height = page_dimensions

        # Calculate scaling and positioning
        img_width_pt = image.width * 72 / self.dpi
        img_height_pt = image.height * 72 / self.dpi

        # Center the image
        x_offset = (page_width - img_width_pt) / 2
        y_offset = (page_height - img_height_pt) / 2

        # Draw the image
        img_reader = ImageReader(image)
        c.drawImage(
            img_reader,
            x_offset,
            y_offset,
            width=img_width_pt,
            height=img_height_pt
        )

        # Add registration marks
        self._add_registration_marks(c, page_width, page_height)

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

    def _add_registration_marks(
        self,
        c: canvas,
        page_width: float,
        page_height: float
    ):
        """Add Silhouette registration marks."""
        margin = 10 * mm
        mark_size = 5 * mm
        line_width = 1 * mm

        c.setFillColorRGB(0, 0, 0)

        positions = [
            (margin, page_height - margin),
            (page_width - margin, page_height - margin),
            (margin, margin),
        ]

        for x, y in positions:
            c.rect(x, y - line_width, mark_size, line_width, fill=1, stroke=0)
            c.rect(x, y - mark_size, line_width, mark_size, fill=1, stroke=0)

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
        """Draw cut lines on the PDF (for preview purposes)."""
        c.setStrokeColorRGB(1, 0, 0)  # Red cut lines
        c.setLineWidth(0.5)

        # Scale factors
        scale_x = img_width_pt / img_width_px
        scale_y = img_height_pt / img_height_px

        for card in cards:
            # Convert pixel coordinates to points
            x = x_offset + card["x"] * scale_x
            # PDF y-axis is from bottom, so flip
            y = y_offset + img_height_pt - (card["y"] + card["height"]) * scale_y
            w = card["width"] * scale_x
            h = card["height"] * scale_y

            # Scale corner radius
            card_scale = min(
                card["width"] / (63 * self.dpi / 25.4),
                card["height"] / (88 * self.dpi / 25.4)
            )
            radius = corner_radius_mm * mm * card_scale

            # Draw rounded rectangle
            c.roundRect(x, y, w, h, radius, fill=0, stroke=1)
