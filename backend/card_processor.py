"""
Card Processor Module

Handles card detection and corner rounding for MTG proxy sheets.
Uses OpenCV for edge detection and PIL for image manipulation.
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw
from typing import List, Dict, Tuple, Optional


class CardProcessor:
    """Processes MTG proxy card sheets - detection and corner rounding."""

    def __init__(
        self,
        card_width_mm: float = 63.0,
        card_height_mm: float = 88.0,
        corner_radius_mm: float = 3.0,
        dpi: int = 300
    ):
        """
        Initialize the card processor.

        Args:
            card_width_mm: MTG card width in millimeters
            card_height_mm: MTG card height in millimeters
            corner_radius_mm: Corner radius in millimeters
            dpi: Dots per inch for calculations
        """
        self.card_width_mm = card_width_mm
        self.card_height_mm = card_height_mm
        self.corner_radius_mm = corner_radius_mm
        self.dpi = dpi

        # Convert mm to pixels
        self.mm_to_px = dpi / 25.4
        self.card_width_px = int(card_width_mm * self.mm_to_px)
        self.card_height_px = int(card_height_mm * self.mm_to_px)
        self.corner_radius_px = int(corner_radius_mm * self.mm_to_px)

        # Expected aspect ratio of MTG cards
        self.card_aspect_ratio = card_width_mm / card_height_mm

    def detect_cards(self, image: Image.Image) -> List[Dict]:
        """
        Auto-detect cards in the image using edge detection.

        Args:
            image: PIL Image of the card sheet

        Returns:
            List of card dictionaries with x, y, width, height
        """
        # Convert PIL to OpenCV format
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Edge detection using Canny
        edges = cv2.Canny(blurred, 50, 150)

        # Dilate edges to close gaps
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        cards = []
        img_area = image.width * image.height

        # Estimate expected card size based on image dimensions
        # Assume the sheet has cards filling most of the area
        min_card_area = img_area * 0.01  # At least 1% of image
        max_card_area = img_area * 0.25  # At most 25% of image (for 2x2 grid)

        for contour in contours:
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h

            # Filter by area
            if area < min_card_area or area > max_card_area:
                continue

            # Check aspect ratio (allow some tolerance)
            aspect = w / h if h > 0 else 0
            if not (0.5 < aspect < 1.0):  # MTG cards are taller than wide
                continue

            # Approximate the contour to a polygon
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)

            # Cards should be roughly rectangular (4-8 vertices with rounded corners)
            if 4 <= len(approx) <= 12:
                cards.append({
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h
                })

        # If detection didn't work well, try grid-based approach
        if len(cards) < 2:
            cards = self._detect_by_grid_analysis(image)

        # Sort cards by position (top-to-bottom, left-to-right)
        cards = self._sort_cards(cards)

        # Remove duplicates and overlapping detections
        cards = self._remove_overlapping(cards)

        return cards

    def _detect_by_grid_analysis(self, image: Image.Image) -> List[Dict]:
        """
        Detect cards by analyzing the image for a regular grid pattern.

        Args:
            image: PIL Image

        Returns:
            List of detected card regions
        """
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

        # Use adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # Find horizontal and vertical lines
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))

        horizontal_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel)
        vertical_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel)

        # Combine lines
        grid = cv2.add(horizontal_lines, vertical_lines)

        # Find contours in the grid
        contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        cards = []
        img_area = image.width * image.height

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h

            if area > img_area * 0.01:  # At least 1% of image
                aspect = w / h if h > 0 else 0
                if 0.5 < aspect < 1.0:
                    cards.append({"x": x, "y": y, "width": w, "height": h})

        return cards

    def generate_grid(
        self,
        image: Image.Image,
        cols: int,
        rows: int,
        margin_percent: float = 0.02
    ) -> List[Dict]:
        """
        Generate a regular grid of card positions.

        Args:
            image: PIL Image
            cols: Number of columns
            rows: Number of rows
            margin_percent: Margin as percentage of image dimensions

        Returns:
            List of card regions
        """
        img_width = image.width
        img_height = image.height

        # Calculate margins
        margin_x = int(img_width * margin_percent)
        margin_y = int(img_height * margin_percent)

        # Calculate card dimensions
        usable_width = img_width - (2 * margin_x)
        usable_height = img_height - (2 * margin_y)

        card_width = usable_width // cols
        card_height = usable_height // rows

        cards = []
        for row in range(rows):
            for col in range(cols):
                x = margin_x + (col * card_width)
                y = margin_y + (row * card_height)
                cards.append({
                    "x": x,
                    "y": y,
                    "width": card_width,
                    "height": card_height
                })

        return cards

    def _sort_cards(self, cards: List[Dict]) -> List[Dict]:
        """Sort cards by position (top-to-bottom, left-to-right)."""
        if not cards:
            return cards

        # Calculate average card height for row detection
        avg_height = sum(c["height"] for c in cards) / len(cards)
        row_threshold = avg_height * 0.5

        # Sort primarily by y (row), then by x (column)
        def sort_key(card):
            row_num = int(card["y"] / row_threshold)
            return (row_num, card["x"])

        return sorted(cards, key=sort_key)

    def _remove_overlapping(self, cards: List[Dict]) -> List[Dict]:
        """Remove overlapping card detections, keeping the larger one."""
        if len(cards) <= 1:
            return cards

        filtered = []
        for card in cards:
            is_duplicate = False
            for existing in filtered:
                # Check for significant overlap
                overlap_x = max(0, min(card["x"] + card["width"], existing["x"] + existing["width"]) -
                               max(card["x"], existing["x"]))
                overlap_y = max(0, min(card["y"] + card["height"], existing["y"] + existing["height"]) -
                               max(card["y"], existing["y"]))
                overlap_area = overlap_x * overlap_y

                card_area = card["width"] * card["height"]
                existing_area = existing["width"] * existing["height"]

                # If overlap is more than 50% of either card, it's a duplicate
                if overlap_area > 0.5 * min(card_area, existing_area):
                    is_duplicate = True
                    # Keep the larger one
                    if card_area > existing_area:
                        filtered.remove(existing)
                        filtered.append(card)
                    break

            if not is_duplicate:
                filtered.append(card)

        return filtered

    def round_corners(self, image: Image.Image, cards: List[Dict]) -> Image.Image:
        """
        Apply rounded corner masks to each detected card.

        Args:
            image: Original PIL Image
            cards: List of card regions

        Returns:
            Processed image with rounded corners
        """
        # Create a copy of the image with alpha channel
        if image.mode != 'RGBA':
            result = image.convert('RGBA')
        else:
            result = image.copy()

        for card in cards:
            # Calculate corner radius based on card size
            # Scale the radius proportionally to the detected card size
            scale_x = card["width"] / self.card_width_px
            scale_y = card["height"] / self.card_height_px
            scale = min(scale_x, scale_y)
            radius = int(self.corner_radius_px * scale)

            # Ensure minimum radius
            radius = max(radius, 5)

            # Create rounded rectangle mask for this card
            mask = self._create_rounded_mask(
                card["width"],
                card["height"],
                radius
            )

            # Apply mask to the card region
            result = self._apply_mask_to_region(result, mask, card)

        return result

    def _create_rounded_mask(
        self,
        width: int,
        height: int,
        radius: int
    ) -> Image.Image:
        """
        Create a rounded rectangle mask.

        Args:
            width: Rectangle width
            height: Rectangle height
            radius: Corner radius

        Returns:
            Grayscale mask image (white = keep, black = transparent)
        """
        mask = Image.new('L', (width, height), 0)
        draw = ImageDraw.Draw(mask)

        # Draw rounded rectangle
        draw.rounded_rectangle(
            [(0, 0), (width - 1, height - 1)],
            radius=radius,
            fill=255
        )

        return mask

    def _apply_mask_to_region(
        self,
        image: Image.Image,
        mask: Image.Image,
        region: Dict
    ) -> Image.Image:
        """
        Apply a mask to a specific region of the image.

        Args:
            image: RGBA image
            mask: Grayscale mask
            region: Region dictionary with x, y, width, height

        Returns:
            Image with mask applied to region
        """
        x, y = region["x"], region["y"]
        w, h = region["width"], region["height"]

        # Ensure we don't go out of bounds
        x = max(0, x)
        y = max(0, y)
        w = min(w, image.width - x)
        h = min(h, image.height - y)

        if w <= 0 or h <= 0:
            return image

        # Resize mask if needed
        if mask.size != (w, h):
            mask = mask.resize((w, h), Image.Resampling.LANCZOS)

        # Extract the region
        region_img = image.crop((x, y, x + w, y + h))

        # Create inverted mask for corners (areas to make transparent)
        inverted_mask = Image.eval(mask, lambda px: 255 - px)

        # Get alpha channel
        if region_img.mode == 'RGBA':
            r, g, b, a = region_img.split()
            # Combine existing alpha with our mask
            new_alpha = Image.composite(a, Image.new('L', (w, h), 0), mask)
            region_img = Image.merge('RGBA', (r, g, b, new_alpha))
        else:
            region_img = region_img.convert('RGBA')
            r, g, b, _ = region_img.split()
            region_img = Image.merge('RGBA', (r, g, b, mask))

        # Paste back
        result = image.copy()
        result.paste(region_img, (x, y))

        return result

    def create_detection_preview(
        self,
        image: Image.Image,
        cards: List[Dict]
    ) -> Image.Image:
        """
        Create a preview image with detected card boundaries drawn.

        Args:
            image: Original image
            cards: Detected card regions

        Returns:
            Image with card boundaries overlaid
        """
        # Convert to RGB for drawing
        preview = image.convert('RGB').copy()
        draw = ImageDraw.Draw(preview)

        for i, card in enumerate(cards):
            x, y = card["x"], card["y"]
            w, h = card["width"], card["height"]

            # Draw rectangle around card
            draw.rectangle(
                [(x, y), (x + w, y + h)],
                outline=(0, 255, 0),
                width=3
            )

            # Draw card number
            draw.text(
                (x + 10, y + 10),
                f"#{i + 1}",
                fill=(255, 0, 0)
            )

            # Draw corner radius preview circles
            radius = int(self.corner_radius_px * min(w / self.card_width_px, h / self.card_height_px))
            radius = max(radius, 5)

            # Top-left corner
            draw.arc([(x, y), (x + 2*radius, y + 2*radius)], 180, 270, fill=(255, 0, 0), width=2)
            # Top-right corner
            draw.arc([(x + w - 2*radius, y), (x + w, y + 2*radius)], 270, 360, fill=(255, 0, 0), width=2)
            # Bottom-left corner
            draw.arc([(x, y + h - 2*radius), (x + 2*radius, y + h)], 90, 180, fill=(255, 0, 0), width=2)
            # Bottom-right corner
            draw.arc([(x + w - 2*radius, y + h - 2*radius), (x + w, y + h)], 0, 90, fill=(255, 0, 0), width=2)

        return preview
