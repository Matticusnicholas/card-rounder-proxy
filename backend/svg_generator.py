"""
SVG Generator Module

Generates SVG cut files with registration marks for Silhouette Portrait 4.
The cut files include:
- Registration marks for print-and-cut alignment
- Rounded rectangle cut paths for each card
"""

import svgwrite
from typing import List, Dict


class SilhouetteSVGGenerator:
    """Generates SVG cut files compatible with Silhouette Portrait 4."""

    # Silhouette registration mark specifications
    REG_MARK_SIZE_MM = 5.0  # Size of registration mark squares
    REG_MARK_MARGIN_MM = 10.0  # Margin from edge to registration marks
    REG_MARK_THICKNESS_MM = 1.0  # Line thickness for registration marks

    def __init__(
        self,
        image_width_mm: float,
        image_height_mm: float,
        corner_radius_mm: float = 3.0,
        dpi: int = 300
    ):
        """
        Initialize the SVG generator.

        Args:
            image_width_mm: Image width in millimeters
            image_height_mm: Image height in millimeters
            corner_radius_mm: Corner radius for cards in millimeters
            dpi: Dots per inch for pixel-to-mm conversion
        """
        self.image_width_mm = image_width_mm
        self.image_height_mm = image_height_mm
        self.corner_radius_mm = corner_radius_mm
        self.dpi = dpi
        self.px_to_mm = 25.4 / dpi

    def generate(
        self,
        cards: List[Dict],
        image_width_px: int,
        image_height_px: int
    ) -> str:
        """
        Generate SVG cut file with registration marks and cut paths.

        Args:
            cards: List of card regions (in pixels)
            image_width_px: Image width in pixels
            image_height_px: Image height in pixels

        Returns:
            SVG content as string
        """
        # Create SVG with mm units
        dwg = svgwrite.Drawing(
            size=(f"{self.image_width_mm}mm", f"{self.image_height_mm}mm"),
            viewBox=f"0 0 {self.image_width_mm} {self.image_height_mm}"
        )

        # Add metadata for Silhouette software
        dwg.attribs['xmlns:silhouette'] = 'http://www.silhouetteamerica.com/silhouette'

        # Create groups for organization
        reg_marks_group = dwg.g(id="registration-marks")
        cut_paths_group = dwg.g(id="cut-paths")

        # Add registration marks
        self._add_registration_marks(dwg, reg_marks_group)

        # Add cut paths for each card
        for i, card in enumerate(cards):
            card_path = self._create_card_cut_path(
                dwg, card, image_width_px, image_height_px, i
            )
            cut_paths_group.add(card_path)

        dwg.add(reg_marks_group)
        dwg.add(cut_paths_group)

        return dwg.tostring()

    def _add_registration_marks(self, dwg: svgwrite.Drawing, group):
        """
        Add Silhouette-compatible registration marks.

        The Silhouette Portrait 4 uses a specific pattern of registration marks:
        - Square marks in corners
        - The marks are used by the optical sensor to align cuts with the print

        Args:
            dwg: SVG Drawing object
            group: Group to add marks to
        """
        mark_size = self.REG_MARK_SIZE_MM
        margin = self.REG_MARK_MARGIN_MM
        thickness = self.REG_MARK_THICKNESS_MM

        # Registration mark positions (corners + optional centers)
        positions = [
            # Top-left
            (margin, margin),
            # Top-right
            (self.image_width_mm - margin - mark_size, margin),
            # Bottom-left
            (margin, self.image_height_mm - margin - mark_size),
            # Bottom-right (optional, some Silhouette patterns use only 3)
            # (self.image_width_mm - margin - mark_size, self.image_height_mm - margin - mark_size),
        ]

        for x, y in positions:
            # Create L-shaped registration mark (Silhouette style)
            # Horizontal part
            group.add(dwg.rect(
                insert=(x, y),
                size=(mark_size, thickness),
                fill="black",
                stroke="none"
            ))
            # Vertical part
            group.add(dwg.rect(
                insert=(x, y),
                size=(thickness, mark_size),
                fill="black",
                stroke="none"
            ))

        # Add type 2 registration marks (filled squares) as alternative
        # These are placed at the outer corners
        alt_positions = [
            (margin + mark_size + 2, margin),  # Near top-left
            (self.image_width_mm - margin - 3, margin),  # Near top-right
            (margin, self.image_height_mm - margin - 3),  # Near bottom-left
        ]

        for x, y in alt_positions:
            group.add(dwg.rect(
                insert=(x, y),
                size=(2, 2),
                fill="black",
                stroke="none"
            ))

    def _create_card_cut_path(
        self,
        dwg: svgwrite.Drawing,
        card: Dict,
        image_width_px: int,
        image_height_px: int,
        index: int
    ) -> svgwrite.path.Path:
        """
        Create a rounded rectangle cut path for a single card.

        Args:
            dwg: SVG Drawing object
            card: Card region dict with x, y, width, height (in pixels)
            image_width_px: Image width in pixels
            image_height_px: Image height in pixels
            index: Card index for naming

        Returns:
            SVG Path element
        """
        # Convert pixel coordinates to mm
        x = card["x"] * self.px_to_mm
        y = card["y"] * self.px_to_mm
        w = card["width"] * self.px_to_mm
        h = card["height"] * self.px_to_mm

        # Scale corner radius based on card size
        # Assuming standard MTG card is 63mm x 88mm
        scale = min(w / 63.0, h / 88.0)
        radius = self.corner_radius_mm * scale
        radius = max(radius, 1.0)  # Minimum 1mm radius

        # Create rounded rectangle path
        path_data = self._rounded_rect_path(x, y, w, h, radius)

        path = dwg.path(
            d=path_data,
            id=f"card-{index}",
            fill="none",
            stroke="red",  # Cut lines are typically red in Silhouette Studio
            stroke_width="0.1mm"
        )

        # Add Silhouette-specific attributes for cut settings
        path.attribs['data-cut-type'] = 'cut'

        return path

    def _rounded_rect_path(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        radius: float
    ) -> str:
        """
        Generate SVG path data for a rounded rectangle.

        Args:
            x: X position
            y: Y position
            width: Rectangle width
            height: Rectangle height
            radius: Corner radius

        Returns:
            SVG path data string
        """
        r = min(radius, width / 2, height / 2)

        # Path starts at top-left corner (after the arc)
        path = f"M {x + r} {y}"

        # Top edge
        path += f" L {x + width - r} {y}"

        # Top-right corner
        path += f" A {r} {r} 0 0 1 {x + width} {y + r}"

        # Right edge
        path += f" L {x + width} {y + height - r}"

        # Bottom-right corner
        path += f" A {r} {r} 0 0 1 {x + width - r} {y + height}"

        # Bottom edge
        path += f" L {x + r} {y + height}"

        # Bottom-left corner
        path += f" A {r} {r} 0 0 1 {x} {y + height - r}"

        # Left edge
        path += f" L {x} {y + r}"

        # Top-left corner
        path += f" A {r} {r} 0 0 1 {x + r} {y}"

        # Close path
        path += " Z"

        return path

    def generate_with_bleed(
        self,
        cards: List[Dict],
        image_width_px: int,
        image_height_px: int,
        bleed_mm: float = 1.0
    ) -> str:
        """
        Generate SVG with bleed area (cut lines slightly inside the card edges).

        Args:
            cards: List of card regions
            image_width_px: Image width in pixels
            image_height_px: Image height in pixels
            bleed_mm: Bleed distance in mm (cut line moved inward)

        Returns:
            SVG content as string
        """
        # Adjust card regions to account for bleed
        adjusted_cards = []
        for card in cards:
            bleed_px = bleed_mm / self.px_to_mm
            adjusted_cards.append({
                "x": card["x"] + bleed_px,
                "y": card["y"] + bleed_px,
                "width": card["width"] - (2 * bleed_px),
                "height": card["height"] - (2 * bleed_px)
            })

        return self.generate(adjusted_cards, image_width_px, image_height_px)


class SilhouetteStudioExporter:
    """Export to Silhouette Studio native format (.studio3)."""

    def __init__(self):
        """
        Note: .studio3 is a proprietary format.
        This class provides SVG export that's compatible with Silhouette Studio import.
        """
        pass

    @staticmethod
    def create_compatible_svg(
        svg_generator: SilhouetteSVGGenerator,
        cards: List[Dict],
        image_width_px: int,
        image_height_px: int
    ) -> str:
        """
        Create an SVG that's optimized for Silhouette Studio import.

        Silhouette Studio preferences:
        - Uses mm as default unit
        - Red stroke (#FF0000) for cut lines
        - No fill on cut paths
        - Specific registration mark pattern

        Args:
            svg_generator: SVG generator instance
            cards: Card regions
            image_width_px: Image width
            image_height_px: Image height

        Returns:
            SVG string optimized for Silhouette Studio
        """
        return svg_generator.generate(cards, image_width_px, image_height_px)


def generate_print_registration_overlay(
    width_mm: float,
    height_mm: float
) -> str:
    """
    Generate a separate SVG with just registration marks for printing.

    This can be composited with the print image before printing,
    ensuring the registration marks are printed for the cutter to read.

    Args:
        width_mm: Page width in mm
        height_mm: Page height in mm

    Returns:
        SVG string with registration marks only
    """
    dwg = svgwrite.Drawing(
        size=(f"{width_mm}mm", f"{height_mm}mm"),
        viewBox=f"0 0 {width_mm} {height_mm}"
    )

    margin = 10.0
    mark_size = 5.0
    thickness = 1.0

    # Three-point registration (top-left, top-right, bottom-left)
    positions = [
        (margin, margin),
        (width_mm - margin - mark_size, margin),
        (margin, height_mm - margin - mark_size),
    ]

    for x, y in positions:
        # L-shaped mark
        dwg.add(dwg.rect(
            insert=(x, y),
            size=(mark_size, thickness),
            fill="black"
        ))
        dwg.add(dwg.rect(
            insert=(x, y),
            size=(thickness, mark_size),
            fill="black"
        ))

    return dwg.tostring()
