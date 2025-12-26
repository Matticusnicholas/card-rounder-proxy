"""
Card Processor Module

Handles card detection and corner rounding for MTG proxy sheets.
Uses OpenCV for edge detection and PIL for image manipulation.
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw
from typing import List, Dict


class CardProcessor:
    """Processes MTG proxy card sheets - detection and corner rounding."""

    def __init__(
        self,
        card_width_mm: float = 63.0,
        card_height_mm: float = 88.0,
        corner_radius_mm: float = 3.0,
        dpi: int = 300
    ):
        self.card_width_mm = card_width_mm
        self.card_height_mm = card_height_mm
        self.corner_radius_mm = corner_radius_mm
        self.dpi = dpi

        # Convert mm to pixels
        self.mm_to_px = dpi / 25.4
        self.card_width_px = int(card_width_mm * self.mm_to_px)
        self.card_height_px = int(card_height_mm * self.mm_to_px)
        self.corner_radius_px = int(corner_radius_mm * self.mm_to_px)

        self.card_aspect_ratio = card_width_mm / card_height_mm

    def detect_cards(self, image: Image.Image) -> List[Dict]:
        """Auto-detect cards in the image using edge detection."""
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=2)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        cards = []
        img_area = image.width * image.height
        min_card_area = img_area * 0.01
        max_card_area = img_area * 0.25

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h

            if area < min_card_area or area > max_card_area:
                continue

            aspect = w / h if h > 0 else 0
            if not (0.5 < aspect < 1.0):
                continue

            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)

            if 4 <= len(approx) <= 12:
                cards.append({"x": x, "y": y, "width": w, "height": h})

        if len(cards) < 2:
            cards = self._detect_by_grid_analysis(image)

        cards = self._sort_cards(cards)
        cards = self._remove_overlapping(cards)
        return cards

    def _detect_by_grid_analysis(self, image: Image.Image) -> List[Dict]:
        """Detect cards by analyzing for a regular grid pattern."""
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        horizontal_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel)
        vertical_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel)

        grid = cv2.add(horizontal_lines, vertical_lines)
        contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        cards = []
        img_area = image.width * image.height

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w * h > img_area * 0.01:
                aspect = w / h if h > 0 else 0
                if 0.5 < aspect < 1.0:
                    cards.append({"x": x, "y": y, "width": w, "height": h})

        return cards

    def generate_grid(self, image: Image.Image, cols: int, rows: int, margin_percent: float = 0.0) -> List[Dict]:
        """Generate a regular grid of card positions."""
        img_width = image.width
        img_height = image.height

        margin_x = int(img_width * margin_percent)
        margin_y = int(img_height * margin_percent)
        usable_width = img_width - (2 * margin_x)
        usable_height = img_height - (2 * margin_y)

        card_width = usable_width // cols
        card_height = usable_height // rows

        cards = []
        for row in range(rows):
            for col in range(cols):
                x = margin_x + (col * card_width)
                y = margin_y + (row * card_height)
                cards.append({"x": x, "y": y, "width": card_width, "height": card_height})

        return cards

    def _sort_cards(self, cards: List[Dict]) -> List[Dict]:
        """Sort cards top-to-bottom, left-to-right."""
        if not cards:
            return cards
        avg_height = sum(c["height"] for c in cards) / len(cards)
        row_threshold = avg_height * 0.5

        def sort_key(card):
            return (int(card["y"] / row_threshold), card["x"])
        return sorted(cards, key=sort_key)

    def _remove_overlapping(self, cards: List[Dict]) -> List[Dict]:
        """Remove overlapping detections."""
        if len(cards) <= 1:
            return cards

        filtered = []
        for card in cards:
            is_duplicate = False
            for existing in filtered:
                overlap_x = max(0, min(card["x"] + card["width"], existing["x"] + existing["width"]) - max(card["x"], existing["x"]))
                overlap_y = max(0, min(card["y"] + card["height"], existing["y"] + existing["height"]) - max(card["y"], existing["y"]))
                overlap_area = overlap_x * overlap_y
                card_area = card["width"] * card["height"]
                existing_area = existing["width"] * existing["height"]

                if overlap_area > 0.5 * min(card_area, existing_area):
                    is_duplicate = True
                    if card_area > existing_area:
                        filtered.remove(existing)
                        filtered.append(card)
                    break

            if not is_duplicate:
                filtered.append(card)

        return filtered

    def round_corners(self, image: Image.Image, cards: List[Dict]) -> Image.Image:
        """
        Apply rounded corners to each card by filling corner areas with white.
        """
        # Convert to RGB
        result = image.convert('RGB') if image.mode != 'RGB' else image.copy()

        for card in cards:
            x, y = card["x"], card["y"]
            w, h = card["width"], card["height"]

            # Calculate radius proportional to card size
            scale = min(w / self.card_width_px, h / self.card_height_px)
            radius = int(self.corner_radius_px * scale)
            radius = max(radius, 5)

            # Apply corner rounding to this card
            result = self._round_card_corners(result, x, y, w, h, radius)

        return result

    def _round_card_corners(self, image: Image.Image, x: int, y: int, w: int, h: int, radius: int) -> Image.Image:
        """
        Round the corners of a single card by painting white in the corner areas.
        """
        # Bounds check
        x = max(0, x)
        y = max(0, y)
        w = min(w, image.width - x)
        h = min(h, image.height - y)

        if w <= 0 or h <= 0 or radius <= 0:
            return image

        result = image.copy()

        # Extract the card region
        card_img = result.crop((x, y, x + w, y + h))

        # Create a mask for the rounded rectangle (white inside, black outside)
        mask = Image.new('L', (w, h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([(0, 0), (w - 1, h - 1)], radius=radius, fill=255)

        # Create inverse mask (white where corners should be white)
        inv_mask = Image.eval(mask, lambda px: 255 - px)

        # Create white image for corners
        white = Image.new('RGB', (w, h), (255, 255, 255))

        # Composite: use card image where mask is white, white where mask is black (corners)
        rounded_card = Image.composite(card_img, white, mask)

        # Paste back
        result.paste(rounded_card, (x, y))

        return result

    def create_detection_preview(self, image: Image.Image, cards: List[Dict]) -> Image.Image:
        """Create preview with detected card boundaries."""
        preview = image.convert('RGB').copy()
        draw = ImageDraw.Draw(preview)

        for i, card in enumerate(cards):
            x, y = card["x"], card["y"]
            w, h = card["width"], card["height"]

            draw.rectangle([(x, y), (x + w, y + h)], outline=(0, 255, 0), width=3)
            draw.text((x + 10, y + 10), f"#{i + 1}", fill=(255, 0, 0))

            radius = int(self.corner_radius_px * min(w / self.card_width_px, h / self.card_height_px))
            radius = max(radius, 5)

            # Draw corner arcs
            draw.arc([(x, y), (x + 2*radius, y + 2*radius)], 180, 270, fill=(255, 0, 0), width=2)
            draw.arc([(x + w - 2*radius, y), (x + w, y + 2*radius)], 270, 360, fill=(255, 0, 0), width=2)
            draw.arc([(x, y + h - 2*radius), (x + 2*radius, y + h)], 90, 180, fill=(255, 0, 0), width=2)
            draw.arc([(x + w - 2*radius, y + h - 2*radius), (x + w, y + h)], 0, 90, fill=(255, 0, 0), width=2)

        return preview
