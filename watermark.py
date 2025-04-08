"""
Photography Watermarking Script - Apply Professional Text Watermarks to Images

This Python script allows users to apply professional-looking watermarks to photos,
similar to those used by photographers to protect their work while still allowing
preview sharing. The script focuses on creating diagonal repeating text patterns
that cover the entire image, making it difficult to crop or remove.

Key Features:
1. **Diagonal Repeating Text Pattern**:
   - Creates a professional repeating watermark pattern similar to those used by photographers
   - Pattern fully covers the image to prevent unauthorized cropping

2. **Customizable Text and Appearance**:
   - Control text content, font, size, color, and opacity
   - Adjust pattern density and angle

3. **Photographer-friendly Defaults**:
   - Default settings optimized for typical photography watermarking
   - Subtle but effective watermarks that don't completely obscure the image

Example Usage:
    python watermark.py -i photo.jpg -t "© Jane Doe Photography"
    python watermark.py -i photo.jpg -t "SAMPLE" --density 0.8 --opacity 0.3 --angle 45
"""

import argparse
from PIL import Image, ImageDraw, ImageFont, ImageColor, ImageFilter
import os
import math
import sys
import textwrap
from pathlib import Path

# Constants
DEFAULT_WATERMARK_PATH = 'watermark-logo.png'
DEFAULT_POSITION = 'center'  # Changed from bottom-right to center
DEFAULT_SCALE = 0.2
DEFAULT_OPACITY = 0.3  # Lower opacity for photography watermarks (more subtle)
DEFAULT_PADDING = 10
DEFAULT_FONT_PATH = None
DEFAULT_FONT_SIZE = 24  # Smaller size for repeating watermarks
DEFAULT_FONT_COLOR = '#ffffff'  # White
DEFAULT_TEXT_ANGLE = 45  # 45-degree angle is standard for photo watermarks
DEFAULT_DENSITY = 0.5  # Controls spacing between repeats (lower = more space)
DEFAULT_TEXT_OUTLINE_WIDTH = 1  # Thinner outline for subtlety
DEFAULT_TEXT_OUTLINE_COLOR = '#000000'  # Black outline
SUPPORTED_EXTENSIONS = ['.jpg', '.jpeg', '.png']


def main():
    """Entry point of the script."""
    args = parse_arguments()

    try:
        base_image = load_image(args.input)

        # Determine if using text or image watermark
        if args.text:
            # Generate diagonal repeating text watermark (photography style)
            watermark = create_photo_text_watermark(
                base_image.size,
                args.text,
                args.font,
                args.font_size,
                args.font_color,
                args.outline_color,
                args.outline_width,
                args.angle,
                args.density
            )

            # Apply opacity to the watermark
            watermark = set_opacity(watermark, args.opacity)

            # For text watermarks, we always center the pattern over the entire image
            position = (0, 0)  # Full overlay starting at top-left
        else:
            # Use image watermark
            watermark = load_image(args.watermark)
            watermark = resize_watermark(base_image, watermark, args.scale)
            watermark = set_opacity(watermark, args.opacity)
            position = calculate_position(base_image, watermark, args.position)

        # Apply the watermark
        watermarked_image = apply_watermark(base_image, watermark, position)

        # Determine output path
        if args.output:
            output_path = args.output
        else:
            input_name, input_ext = os.path.splitext(args.input)
            output_ext = input_ext if input_ext.lower() in SUPPORTED_EXTENSIONS else '.png'
            output_path = f"{input_name}_wm{output_ext}"

        save_image(watermarked_image, output_path)

        print(f"Watermark applied successfully! Saved to {output_path}")
    except Exception as e:
        print(f"An error occurred: {e}")


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Apply professional photography-style watermarks to images.",
        epilog="""
Examples:
  # Professional photography watermark
  python watermark.py -i photo.jpg -t "© Jane Doe Photography" 
  python watermark.py -i photo.jpg -t "SAMPLE" --density 0.8 --opacity 0.25 --angle 45

  # Legacy image watermark functionality
  python watermark.py -i photo.jpg -w custom_watermark.png -p bottom-right -s 0.2 -a 0.7

For more information, use the -h or --help option with each argument.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Required arguments
    parser.add_argument('-i', '--input', required=True, help="Path to the input image.")

    # Watermark group - either image or text
    watermark_group = parser.add_mutually_exclusive_group()
    watermark_group.add_argument('-w', '--watermark', default=DEFAULT_WATERMARK_PATH,
                                 help=f"Path to the watermark image. Default: {DEFAULT_WATERMARK_PATH}")
    watermark_group.add_argument('-t', '--text', help="Text to use as watermark (e.g., '© Your Name')")

    # Text watermark specific options
    text_group = parser.add_argument_group('Text Watermark Options')
    text_group.add_argument('--font', default=DEFAULT_FONT_PATH,
                            help="Path to a TrueType font file. Uses default font if not specified.")
    text_group.add_argument('--font-size', type=int, default=DEFAULT_FONT_SIZE,
                            help=f"Font size for text watermark. Default: {DEFAULT_FONT_SIZE}")
    text_group.add_argument('--font-color', default=DEFAULT_FONT_COLOR,
                            help=f"Font color in hex format (e.g., #FFFFFF for white). Default: {DEFAULT_FONT_COLOR}")
    text_group.add_argument('--outline-color', default=DEFAULT_TEXT_OUTLINE_COLOR,
                            help=f"Outline color for text in hex format. Default: {DEFAULT_TEXT_OUTLINE_COLOR}")
    text_group.add_argument('--outline-width', type=int, default=DEFAULT_TEXT_OUTLINE_WIDTH,
                            help=f"Width of text outline in pixels. Default: {DEFAULT_TEXT_OUTLINE_WIDTH}")
    text_group.add_argument('--angle', type=float, default=DEFAULT_TEXT_ANGLE,
                            help=f"Rotation angle for text watermark in degrees. Default: {DEFAULT_TEXT_ANGLE}")
    text_group.add_argument('--density', type=float, default=DEFAULT_DENSITY,
                            help=f"Density of the repeating pattern (0.1-1.0). Lower values create more space between text. Default: {DEFAULT_DENSITY}")

    # Common options
    parser.add_argument('-o', '--output',
                        help="Path to save the watermarked image. If not provided, '_wm' will be appended to the input filename.")
    parser.add_argument('-p', '--position',
                        choices=['top-left', 'top-right', 'bottom-left', 'bottom-right', 'center'],
                        default=DEFAULT_POSITION,
                        help=f"Position for image watermarks (ignored for text watermarks). Default: {DEFAULT_POSITION}")
    parser.add_argument('-s', '--scale', type=float, default=DEFAULT_SCALE,
                        help=f"Scale factor for image watermarks (0 to 1). Default: {DEFAULT_SCALE}")
    parser.add_argument('-a', '--opacity', type=float, default=DEFAULT_OPACITY,
                        help=f"Opacity level for the watermark (0 to 1). Default: {DEFAULT_OPACITY}")

    args = parser.parse_args()
    return args


def load_image(image_path):
    """Load an image from the specified path."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"The file '{image_path}' does not exist.")
    try:
        return Image.open(image_path).convert("RGBA")
    except IOError:
        raise Exception(f"Unable to load image: {image_path}")


def get_system_font():
    """Try to find a suitable system font."""
    # Common font locations and names
    font_options = [
        # Windows fonts
        "Arial.ttf", "arial.ttf",
        "Verdana.ttf", "verdana.ttf",
        "Tahoma.ttf", "tahoma.ttf",
        "Times.ttf", "times.ttf",
        "TimesNewRoman.ttf", "timesnewroman.ttf",
        # Linux fonts
        "DejaVuSans.ttf", "DejaVuSans-Bold.ttf",
        # Mac fonts
        "Helvetica.ttf", "helvetica.ttf",
        # System paths
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\verdana.ttf"
    ]

    for font_name in font_options:
        try:
            return ImageFont.truetype(font_name, 12)  # Test with a small size
        except IOError:
            continue

    # If all fonts fail, fall back to default
    return ImageFont.load_default()


def create_single_text_watermark(text, font, font_size, font_color, outline_color, outline_width):
    """Create a single instance of the text watermark."""
    # Create a temporary transparent image
    temp_img = Image.new('RGBA', (1, 1), (255, 255, 255, 0))
    temp_draw = ImageDraw.Draw(temp_img)

    # Calculate text size
    text_bbox = temp_draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    # Create the actual text image with padding for outline
    padding = outline_width * 2
    text_img = Image.new('RGBA', (text_width + padding * 2, text_height + padding * 2), (255, 255, 255, 0))
    draw = ImageDraw.Draw(text_img)

    # Convert colors to RGB tuples
    try:
        font_color_rgb = ImageColor.getcolor(font_color, "RGBA")
    except ValueError:
        print(f"Warning: Invalid font color '{font_color}'. Using white.")
        font_color_rgb = (255, 255, 255, 255)

    try:
        outline_color_rgb = ImageColor.getcolor(outline_color, "RGBA")
    except ValueError:
        print(f"Warning: Invalid outline color '{outline_color}'. Using black.")
        outline_color_rgb = (0, 0, 0, 255)

    # Draw outline by drawing text multiple times with offsets
    if outline_width > 0:
        for offset_x in range(-outline_width, outline_width + 1):
            for offset_y in range(-outline_width, outline_width + 1):
                if offset_x == 0 and offset_y == 0:
                    continue
                draw.text((padding + offset_x, padding + offset_y), text, font=font, fill=outline_color_rgb)

    # Draw the main text
    draw.text((padding, padding), text, font=font, fill=font_color_rgb)

    return text_img


def create_photo_text_watermark(base_size, text, font_path, font_size, font_color,
                                outline_color, outline_width, angle, density):
    """Create a diagonal repeating text watermark pattern across the entire image."""
    base_width, base_height = base_size

    # Load font
    try:
        if font_path:
            font = ImageFont.truetype(font_path, font_size)
        else:
            font = get_system_font()
            if isinstance(font, ImageFont.ImageFont):  # If it's the default PIL font
                # Scale default font size (it's usually small)
                font_size = int(font_size * 1.5)
    except IOError:
        print(f"Warning: Could not load font from {font_path}. Using system font.")
        font = get_system_font()

    # Create a single text watermark
    single_text = create_single_text_watermark(
        text, font, font_size, font_color, outline_color, outline_width
    )

    # Calculate spacing based on density and image size
    # Higher density = smaller spacing between watermarks
    diagonal_length = math.sqrt(base_width ** 2 + base_height ** 2)
    spacing_factor = 1.0 - density  # Invert density (higher density = lower spacing)
    spacing_factor = max(0.2, min(1.0, spacing_factor))  # Clamp between 0.2 and 1.0

    # Calculate text spacing as a function of text length and density
    text_width, text_height = single_text.size
    base_spacing = int(max(text_width, text_height) * 2.5 * spacing_factor)  # Base spacing is 2.5x text size

    # Create pattern canvas (larger than image to ensure full coverage)
    # Calculate pattern size with enough margin
    pattern_width = base_width + (2 * text_width)
    pattern_height = base_height + (2 * text_height)
    pattern = Image.new('RGBA', (pattern_width, pattern_height), (255, 255, 255, 0))

    # Rotate the text for diagonal placement
    rotated_text = single_text.rotate(angle, expand=True, resample=Image.BICUBIC)
    rotated_width, rotated_height = rotated_text.size

    # Calculate grid parameters for placing the watermarks
    # Use diagonal lines at the specified angle
    angle_rad = math.radians(angle)
    dx = int(math.cos(angle_rad) * base_spacing)
    dy = int(math.sin(angle_rad) * base_spacing)

    # Calculate perpendicular direction for offset rows
    perp_dx = int(math.cos(angle_rad + math.pi / 2) * base_spacing)
    perp_dy = int(math.sin(angle_rad + math.pi / 2) * base_spacing)

    # Calculate how many lines we need
    diagonal_count = int(diagonal_length / base_spacing) * 2  # Multiply by 2 for safety

    # Start position (negative offsets to ensure coverage)
    start_x = -rotated_width
    start_y = -rotated_height

    # Create diagonal lines of text
    for i in range(-diagonal_count, diagonal_count):
        line_start_x = start_x + (i * perp_dx)
        line_start_y = start_y + (i * perp_dy)

        # Calculate how many texts to place on this line
        line_length = diagonal_length * 1.5  # Extra length for safety
        text_count = int(line_length / base_spacing) + 1

        for j in range(text_count):
            x = line_start_x + (j * dx)
            y = line_start_y + (j * dy)

            # Only place if within or near the pattern bounds
            if (-rotated_width <= x <= pattern_width and
                    -rotated_height <= y <= pattern_height):
                pattern.paste(rotated_text, (x, y), rotated_text)

    # Crop the pattern to match the base image size
    left = (pattern_width - base_width) // 2
    top = (pattern_height - base_height) // 2
    right = left + base_width
    bottom = top + base_height

    return pattern.crop((left, top, right, bottom))


def resize_watermark(base_image, watermark, scale_factor):
    """Resize the watermark image relative to the base image."""
    base_width, base_height = base_image.size
    watermark_width = int(base_width * scale_factor)
    watermark_height = int(watermark.size[1] * (watermark_width / watermark.size[0]))
    return watermark.resize((watermark_width, watermark_height), Image.LANCZOS)


def set_opacity(watermark, opacity):
    """Adjust the opacity of the watermark."""
    watermark = watermark.copy()
    alpha = watermark.split()[3]
    alpha = Image.blend(Image.new('L', watermark.size, 0), alpha, opacity)
    watermark.putalpha(alpha)
    return watermark


def calculate_position(base_image, watermark, position):
    """Calculate the position where the watermark should be placed."""
    base_width, base_height = base_image.size
    watermark_width, watermark_height = watermark.size

    if position == 'top-left':
        return (DEFAULT_PADDING, DEFAULT_PADDING)
    elif position == 'top-right':
        return (base_width - watermark_width - DEFAULT_PADDING, DEFAULT_PADDING)
    elif position == 'bottom-left':
        return (DEFAULT_PADDING, base_height - watermark_height - DEFAULT_PADDING)
    elif position == 'bottom-right':
        return (base_width - watermark_width - DEFAULT_PADDING, base_height - watermark_height - DEFAULT_PADDING)
    elif position == 'center':
        return ((base_width - watermark_width) // 2, (base_height - watermark_height) // 2)


def apply_watermark(base_image, watermark, position):
    """Overlay the watermark on the base image at the specified position."""
    result = base_image.copy()
    result.paste(watermark, position, watermark)
    return result


def save_image(image, output_path):
    """Save the processed image to the specified output path."""
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if output_path.lower().endswith(('.jpg', '.jpeg')):
        image = image.convert('RGB')
    image.save(output_path)


if __name__ == "__main__":
    main()