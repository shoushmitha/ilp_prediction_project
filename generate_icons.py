"""
generate_icons.py
Creates PNG icons (16x16, 48x48, 128x128) for the Chrome extension
using only the Pillow library (no external images needed).
Run once: python generate_icons.py
"""

import os
from PIL import Image, ImageDraw, ImageFont

def draw_icon(size: int, output_path: str):
    """
    Draws a cricket-themed gradient circle with a bat emoji–style glyph.
    Falls back to a simple colored disc if fonts aren't available.
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background gradient circle (simulate with concentric circles)
    for i in range(size // 2, 0, -1):
        ratio = i / (size // 2)
        r = int(15  + (247 - 15)  * (1 - ratio))   # #0f → #f7 (gold-orange)
        g = int(12  + (151 - 12)  * (1 - ratio))
        b = int(41  + (30  - 41)  * (1 - ratio))
        draw.ellipse(
            [size // 2 - i, size // 2 - i, size // 2 + i, size // 2 + i],
            fill=(r, g, b, 255),
        )

    # Outer gold ring
    ring_w = max(1, size // 16)
    draw.ellipse(
        [ring_w, ring_w, size - ring_w, size - ring_w],
        outline=(255, 210, 0, 255),
        width=ring_w,
    )

    # Cricket bat emoji text in centre
    emoji = "🏏"
    font_size = max(8, int(size * 0.45))
    font = None
    # Try common system emoji fonts
    for font_path in [
        "C:/Windows/Fonts/seguiemj.ttf",   # Windows Segoe UI Emoji
        "C:/Windows/Fonts/arial.ttf",
        "/System/Library/Fonts/Apple Color Emoji.ttc",
    ]:
        try:
            font = ImageFont.truetype(font_path, font_size)
            break
        except (IOError, OSError):
            continue

    if font:
        bbox = draw.textbbox((0, 0), emoji, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (size - text_w) / 2 - bbox[0]
        y = (size - text_h) / 2 - bbox[1]
        draw.text((x, y), emoji, font=font, embedded_color=True)
    else:
        # Simple fallback: white "I" letter
        fallback_font_size = max(6, int(size * 0.5))
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", fallback_font_size)
        except Exception:
            font = ImageFont.load_default()
        draw.text((size * 0.35, size * 0.25), "I", fill=(255, 255, 255, 255), font=font)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")
    print(f"  [OK] Created: {output_path} ({size}x{size})")


if __name__ == "__main__":
    base = os.path.join(
        os.path.dirname(__file__), "chrome_extension", "icons"
    )
    print("[*] Generating extension icons...")
    for sz in [16, 48, 128]:
        draw_icon(sz, os.path.join(base, f"icon{sz}.png"))
    print("[DONE] Icons saved to chrome_extension/icons/")
