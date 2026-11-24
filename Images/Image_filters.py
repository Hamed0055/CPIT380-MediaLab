"""CPIT-380 MediaLab: image-processing functions.

Filters return independent RGB or RGBA images.
Colour operations keep the input alpha channel. Spatial effects process
colour and alpha together to avoid carrying hidden colours into visible areas.

Install dependencies: python -m pip install Pillow numpy
"""

from __future__ import annotations

import math
from numbers import Real

import numpy as np
from PIL import Image, ImageFilter, ImageOps


# Working image: Normalize unusual Pillow modes while keeping colour and transparency.
def _working_image(image: Image.Image) -> Image.Image:
    if not isinstance(image, Image.Image):
        raise TypeError("image must be a Pillow Image.Image")
    mode = "RGBA" if image.has_transparency_data else "RGB"
    return image if image.mode == mode else image.convert(mode)


# Preserve alpha: Attach the unchanged opacity plane to a new RGB result.
def _preserve_alpha(source: Image.Image, result: Image.Image) -> Image.Image:
    if source.mode == "RGBA":
        result.putalpha(source.getchannel("A"))
    return result


# Map colours: Apply one lookup rule to RGB channels without remapping opacity.
def _map_colours(image: Image.Image, mapping) -> Image.Image:
    image = _working_image(image)
    rgb = image if image.mode == "RGB" else image.convert("RGB")
    return _preserve_alpha(image, rgb.point(mapping))


# Visible histogram: Count luminance levels for every pixel with nonzero opacity.
def _visible_histogram(image: Image.Image) -> list[int]:
    mask = image.getchannel("A") if image.mode == "RGBA" else None
    return image.convert("L").histogram(mask=mask)


# Helper — Parameter Validation: Checks that a slider value is numeric, finite, and within its allowed range.
def _check_number(name: str, value: Real, minimum: float, maximum: float) -> float:
    """Validate a numeric slider value (including non-finite values)."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a number")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return float(value)


# Helper — Image Reconstruction: Converts a numerical RGB array into an 8-bit Pillow image.
def _from_rgb_array(array: np.ndarray) -> Image.Image:
    """Clip a numerical RGB array to valid eight-bit channel values."""
    return Image.fromarray(np.clip(np.rint(array), 0, 255).astype(np.uint8))


# -- Colour transformations -------------------------------------------------


# 01. Posterization: Reduces each colour channel to a chosen number of discrete levels.
def posterize_n_levels(image: Image.Image, levels: int = 6) -> Image.Image:
    """Quantize each RGB channel to `levels` equally spaced values (2..256).

    Formula: output = round(input * (levels - 1) / 255) * 255 / (levels - 1)
    This avoids creating an enormous (height, width, RGB, levels) array.
    """
    if isinstance(levels, bool) or not isinstance(levels, (int, np.integer)):
        raise TypeError("levels must be an integer")
    if not 2 <= levels <= 256:
        raise ValueError("levels must be between 2 and 256")

    step = 255.0 / (levels - 1)
    return _map_colours(image, lambda value: round(round(value / step) * step))


# 02. Sepia: Applies an RGB transformation matrix to create a warm, vintage colour tone.
def sepia_matrix(image: Image.Image) -> Image.Image:
    """Produce a warm sepia colour effect using an RGB transformation matrix."""
    image = _working_image(image)
    r, g, b = (np.asarray(image.getchannel(channel), dtype=np.float32) for channel in "RGB")
    channels = (
        _from_rgb_array(a * r + c * g + d * b)
        for a, c, d in ((0.393, 0.769, 0.189), (0.349, 0.686, 0.168), (0.272, 0.534, 0.131))
    )
    return _preserve_alpha(image, Image.merge("RGB", tuple(channels)))


# 03. Negative: Inverts each RGB channel by subtracting its value from 255.
def negative(image: Image.Image) -> Image.Image:
    """Invert colour channels: R' = 255-R, G' = 255-G, B' = 255-B."""
    return _map_colours(image, lambda value: 255 - value)


# 04. Grayscale: Replaces each pixel with the average intensity of its RGB channels.
def grayscale_average(image: Image.Image) -> Image.Image:
    """Lab-style grayscale: (R + G + B) // 3, repeated in all three channels."""
    image = _working_image(image)
    pixels = np.asarray(image, dtype=np.uint16)
    intensity = (pixels[..., 0] + pixels[..., 1] + pixels[..., 2]) // 3
    gray = Image.fromarray(intensity.astype(np.uint8))
    return _preserve_alpha(image, Image.merge("RGB", (gray, gray, gray)))


# 05. Sunset: Creates a warmer image by reducing the green and blue channels.
def make_sunset(image: Image.Image, factor: float = 0.7) -> Image.Image:
    """Leave red unchanged and reduce green/blue by `factor` (0..1)."""
    factor = _check_number("factor", factor, 0.0, 1.0)
    return adjust_rgb_channels(image, green=factor * 100, blue=factor * 100)


# 06. RGB Adjustment: Independently increases or decreases the red, green, and blue channels.
def adjust_rgb_channels(
    image: Image.Image,
    red: float = 100,
    green: float = 100,
    blue: float = 100,
) -> Image.Image:
    """RGB sliders in percent: 0 removes a channel, 100 is neutral, 200 doubles it."""
    factors = [_check_number(channel, value, 0, 200) / 100
               for channel, value in zip(("red", "green", "blue"), (red, green, blue))]
    table = [min(255, round(value * factor)) for factor in factors for value in range(256)]
    return _map_colours(image, table)


# -- Geometry ---------------------------------------------------------------


# 07. Rotation: Rotates an image counter-clockwise while expanding the canvas to retain its content.
def rotate_image_by_angle(
    image: Image.Image,
    angle_degrees: float,
    fillcolor: tuple[int, int, int] = (255, 255, 255),
    *,
    max_pixels: int | None = None,
) -> Image.Image:
    """Rotate counter-clockwise; expand canvas so corners are not clipped.

    Pillow performs the inverse coordinate mapping and bilinear interpolation.
    This is faster and smoother than the original Python pixel-by-pixel loop.
    """
    angle_degrees = _check_number("angle_degrees", angle_degrees, -3600, 3600)
    if (
        not isinstance(fillcolor, tuple)
        or len(fillcolor) != 3
        or any(
            isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 255
            for v in fillcolor
        )
    ):
        raise ValueError("fillcolor must be a tuple of three integers from 0 to 255")
    image = _working_image(image)
    if max_pixels is not None:
        if angle_degrees % 90:
            angle = math.radians(angle_degrees % 180)
            sine, cosine = abs(math.sin(angle)), abs(math.cos(angle))
            # An expanded centered transform can round outward at both edges.
            width = math.ceil(image.width * cosine + image.height * sine) + 1
            height = math.ceil(image.height * cosine + image.width * sine) + 1
        else:
            width, height = image.size
        if width * height > max_pixels:
            raise ValueError("This angle makes the image too large. Try a smaller turn.")
    background = (0, 0, 0, 0) if image.mode == "RGBA" else fillcolor
    return image.rotate(
        angle_degrees, resample=Image.Resampling.BILINEAR, expand=True, fillcolor=background,
    )


# 08. Horizontal Mirror: Reverses the image from left to right.
def mirror_horizontal(image: Image.Image) -> Image.Image:
    """Flip left/right. Destination at x receives source column width-1-x."""
    return ImageOps.mirror(_working_image(image))


# Vertical mirror: Reverse the order of the rows.
def mirror_vertical(image: Image.Image) -> Image.Image:
    return ImageOps.flip(_working_image(image))


# -- Easy optional filters --------------------------------------------------


# 09. Brightness: Makes an image darker or lighter using a multiplier.
def adjust_brightness(image: Image.Image, factor: float = 1.0) -> Image.Image:
    """Multiply brightness. 0=black, 1=no change, 2=about twice as bright."""
    factor = _check_number("factor", factor, 0.0, 3.0)
    return _map_colours(image, lambda value: min(255, round(value * factor)))


# 10. Contrast: Spreads or compresses RGB values around the image's mean intensity.
def adjust_contrast(image: Image.Image, factor: float = 1.0) -> Image.Image:
    """Adjust separation of light/dark pixels. 0=flat, 1=no change."""
    factor = _check_number("Contrast factor", factor, 0, 3)
    image = _working_image(image)
    if factor == 1:
        return image.copy()
    counts = _visible_histogram(image)
    total_pixels = sum(counts)
    if total_pixels == 0:
        return image.copy()
    mean = sum(i * count for i, count in enumerate(counts)) / total_pixels
    return _map_colours(image, lambda value: max(0, min(255, round(factor * (value - mean) + mean))))


# 11. Gaussian Blur: Softens an image by smoothing neighbouring pixels.
def blur_image(image: Image.Image, radius: float = 2.0) -> Image.Image:
    """Smooth neighbouring pixels using a Gaussian blur kernel."""
    radius = _check_number("radius", radius, 0.0, 20.0)
    image = _working_image(image)
    if radius == 0:
        return image.copy()
    kernel = ImageFilter.GaussianBlur(radius=radius)
    if image.mode == "RGBA":
        # Weight neighbours by opacity before smoothing to prevent hidden-colour halos.
        return image.convert("RGBa").filter(kernel).convert("RGBA")
    return image.filter(kernel)


# 12. Binary Threshold: Converts pixels to black or white based on an intensity threshold.
def binary_threshold(image: Image.Image, threshold: int = 128) -> Image.Image:
    """Turn pixels into black/white using the simple grayscale average."""
    if isinstance(threshold, bool) or not isinstance(threshold, (int, np.integer)):
        raise TypeError("threshold must be an integer")
    if not 0 <= threshold <= 255:
        raise ValueError("threshold must be between 0 and 255")

    return _map_colours(grayscale_average(image), lambda value: 255 if value >= threshold else 0)


# 13. Image Blending: Combines two images using a user-selected mixing ratio.
def blend_images(
    image_a: Image.Image,
    image_b: Image.Image,
    alpha: float = 0.5,
) -> Image.Image:
    """Mix two images: (1-alpha)*A + alpha*B.

    The second image is resized to match the first image's dimensions.
    alpha=0 returns A; alpha=1 returns the resized B.
    """
    alpha = _check_number("alpha", alpha, 0.0, 1.0)
    first, second = _working_image(image_a), _working_image(image_b)
    if alpha == 0:
        return first.copy()
    if second.size != first.size:
        second = second.resize(first.size, resample=Image.Resampling.LANCZOS)
    if alpha == 1:
        return second.copy()

    if first.mode == second.mode == "RGB":
        return Image.merge("RGB", tuple(
            _from_rgb_array(
                (1 - alpha) * np.asarray(first.getchannel(channel), dtype=np.float32)
                + alpha * np.asarray(second.getchannel(channel), dtype=np.float32)
            )
            for channel in "RGB"
        ))

    first = first.convert("RGBA")
    second = second.convert("RGBA")
    first_weight = np.asarray(first.getchannel("A"), dtype=np.float32) * (1 - alpha)
    second_weight = np.asarray(second.getchannel("A"), dtype=np.float32) * alpha
    combined_alpha = first_weight + second_weight
    channels = []
    for channel in "RGB":
        colour = first_weight * np.asarray(first.getchannel(channel), dtype=np.float32)
        colour += second_weight * np.asarray(second.getchannel(channel), dtype=np.float32)
        np.divide(colour, combined_alpha, out=colour, where=combined_alpha > 0)
        channels.append(_from_rgb_array(colour))
    return Image.merge("RGBA", (*channels, _from_rgb_array(combined_alpha)))
