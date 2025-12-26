"""
SVG Generator Module

Generates SVG cut files with registration marks for Silhouette Portrait 4.
"""

import svgwrite
from typing import List, Dict


class SilhouetteSVGGenerator:
    """Generates SVG cut files compatible with Silhouette Portrait 4."""

    # Silhouette registration mark specifications
    REG_MARK_SIZE_MM = 5.0
    REG_MARK_MARGIN_MM = 10.0
    REG_MARK_THICKNESS_MM = 1.0

    def __init__(
        self,
        image_width_mm: float,
        image_height_mm: float,
        corner_radius_mm: float = 3.0,
        dpi: int = 300
    ):
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
        Generate SVG cut file with cut paths for each card.
        Coordinates are relative to the image origin (0,0).
        """
        # SVG dimensions match image dimensions
        dwg = svgwrite.Drawing(
            size=(f"{self.image_width_mm}mm", f"{self.image_height_mm}mm"),
            viewBox=f"0 0 {self.image_width_mm} {self.image_height_mm}"
        )

        cut_paths_group = dwg.g(id="cut-paths")

        # Add cut paths for each card
        for i, card in enumerate(cards):
            # Convert pixel coordinates to mm
            x = card["x"] * self.px_to_mm
            y = card["y"] * self.px_to_mm
            w = card["width"] * self.px_to_mm
            h = card["height"] * self.px_to_mm

            # Scale corner radius based on card size
            scale = min(w / 63.0, h / 88.0)
            radius = self.corner_radius_mm * scale
            radius = max(radius, 1.0)

            # Create rounded rectangle path
            path_data = self._rounded_rect_path(x, y, w, h, radius)

            path = dwg.path(
                d=path_data,
                id=f"card-{i}",
                fill="none",
                stroke="red",
                stroke_width="0.25"
            )
            cut_paths_group.add(path)

        dwg.add(cut_paths_group)
        return dwg.tostring()

    def _rounded_rect_path(self, x: float, y: float, w: float, h: float, r: float) -> str:
        """Generate SVG path data for a rounded rectangle."""
        r = min(r, w / 2, h / 2)

        path = f"M {x + r} {y}"
        path += f" L {x + w - r} {y}"
        path += f" A {r} {r} 0 0 1 {x + w} {y + r}"
        path += f" L {x + w} {y + h - r}"
        path += f" A {r} {r} 0 0 1 {x + w - r} {y + h}"
        path += f" L {x + r} {y + h}"
        path += f" A {r} {r} 0 0 1 {x} {y + h - r}"
        path += f" L {x} {y + r}"
        path += f" A {r} {r} 0 0 1 {x + r} {y}"
        path += " Z"

        return path
