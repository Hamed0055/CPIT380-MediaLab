"""CPIT-380 MediaLab: image-processing functions.

All filters take Pillow images and return NEW RGB Pillow images.
The caller's original image is never modified. Transparent inputs are
flattened over white because this teaching implementation uses RGB channels.

Install dependencies: python -m pip install Pillow numpy
"""

from __future__ import annotations

import math
from numbers import Real

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


# Helper — RGB Conversion: Converts an input image to an independent RGB image on a white background.
def _rgb(image: Image.Image) -> Image.Image:
    """Return an independent RGB copy; flatten transparency over white."""
    if not isinstance(image, Image.Image):
        raise TypeError("image must be a Pillow Image.Image")

    rgba = image.convert("RGBA")
    background = Image.new("RGB", rgba.size, "white")
    background.paste(rgba, mask=rgba.getchannel("A"))
    return background


# Helper — Parameter Validation: Checks that a slider value is numeric, finite, and within its allowed range.
def _check_number(name: str, value: Real, minimum: float, maximum: float) -> float:
    """Validate a numeric slider value (including non-finite values)."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a number")
    numeric = float(value)
    if not math.isfinite(numeric) or not minimum <= numeric <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return numeric


# Helper — Image Reconstruction: Converts a numerical RGB array into an 8-bit Pillow image.
def _from_rgb_array(array: np.ndarray) -> Image.Image:
    """Clip a numerical RGB array to valid eight-bit channel values."""
    return Image.fromarray(np.clip(array, 0, 255).astype(np.uint8))


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

    pixels = np.asarray(_rgb(image), dtype=np.float32)
    step = 255.0 / (levels - 1)
    return _from_rgb_array(np.rint(pixels / step) * step)


# 02. Sepia: Applies an RGB transformation matrix to create a warm, vintage colour tone.
def sepia_matrix(image: Image.Image) -> Image.Image:
    """Produce a warm sepia colour effect using an RGB transformation matrix."""
    pixels = np.asarray(_rgb(image), dtype=np.float32)
    r, g, b = pixels[..., 0], pixels[..., 1], pixels[..., 2]
    result = np.stack(
        (
            0.393 * r + 0.769 * g + 0.189 * b,
            0.349 * r + 0.686 * g + 0.168 * b,
            0.272 * r + 0.534 * g + 0.131 * b,
        ),
        axis=-1,
    )
    return _from_rgb_array(result)


# 03. Negative: Inverts each RGB channel by subtracting its value from 255.
def negative(image: Image.Image) -> Image.Image:
    """Invert colour channels: R' = 255-R, G' = 255-G, B' = 255-B."""
    return ImageOps.invert(_rgb(image))


# 04. Grayscale: Replaces each pixel with the average intensity of its RGB channels.
def grayscale_average(image: Image.Image) -> Image.Image:
    """Lab-style grayscale: (R + G + B) // 3, repeated in all three channels."""
    pixels = np.asarray(_rgb(image), dtype=np.uint16)
    intensity = (pixels[..., 0] + pixels[..., 1] + pixels[..., 2]) // 3
    gray = intensity.astype(np.uint8)
    return Image.fromarray(np.stack((gray, gray, gray), axis=-1))


# 05. Sunset: Creates a warmer image by reducing the green and blue channels.
def make_sunset(image: Image.Image, factor: float = 0.7) -> Image.Image:
    """Leave red unchanged and reduce green/blue by `factor` (0..1)."""
    factor = _check_number("factor", factor, 0.0, 1.0)
    pixels = np.asarray(_rgb(image), dtype=np.float32).copy()
    pixels[..., 1] *= factor
    pixels[..., 2] *= factor
    return _from_rgb_array(pixels)


# 06. RGB Adjustment: Independently increases or decreases the red, green, and blue channels.
def adjust_rgb_channels(
    image: Image.Image,
    red: float = 100,
    green: float = 100,
    blue: float = 100,
) -> Image.Image:
    """RGB sliders in percent: 0 removes a channel, 100 is neutral, 200 doubles it."""
    factors = (
        np.array(
            [
                _check_number("red", red, 0, 200),
                _check_number("green", green, 0, 200),
                _check_number("blue", blue, 0, 200),
            ],
            dtype=np.float32,
        )
        / 100.0
    )
    pixels = np.asarray(_rgb(image), dtype=np.float32)
    return _from_rgb_array(pixels * factors)


# -- Geometry ---------------------------------------------------------------


# 07. Rotation: Rotates an image counter-clockwise while expanding the canvas to retain its content.
def rotate_image_by_angle(
    image: Image.Image,
    angle_degrees: float,
    fillcolor: tuple[int, int, int] = (255, 255, 255),
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
    return _rgb(image).rotate(
        angle_degrees,
        resample=Image.Resampling.BILINEAR,
        expand=True,
        fillcolor=fillcolor,
    )


# 08. Horizontal Mirror: Reverses the image from left to right.
def mirror_horizontal(image: Image.Image) -> Image.Image:
    """Flip left/right. Destination at x receives source column width-1-x."""
    return ImageOps.mirror(_rgb(image))


# -- Easy optional filters --------------------------------------------------


# 09. Brightness: Makes an image darker or lighter using a multiplier.
def adjust_brightness(image: Image.Image, factor: float = 1.0) -> Image.Image:
    """Multiply brightness. 0=black, 1=no change, 2=about twice as bright."""
    factor = _check_number("factor", factor, 0.0, 3.0)
    return ImageEnhance.Brightness(_rgb(image)).enhance(factor)


# 10. Contrast: Adjusts the separation between dark and light tones.
def adjust_contrast(image: Image.Image, factor: float = 1.0) -> Image.Image:
    """Adjust separation of light/dark pixels. 0=flat, 1=no change."""
    factor = _check_number("factor", factor, 0.0, 3.0)
    return ImageEnhance.Contrast(_rgb(image)).enhance(factor)


# 11. Gaussian Blur: Softens an image by smoothing neighbouring pixels.
def blur_image(image: Image.Image, radius: float = 2.0) -> Image.Image:
    """Smooth neighbouring pixels using a Gaussian blur kernel."""
    radius = _check_number("radius", radius, 0.0, 20.0)
    return _rgb(image).filter(ImageFilter.GaussianBlur(radius=radius))


# 12. Binary Threshold: Converts pixels to black or white based on an intensity threshold.
def binary_threshold(image: Image.Image, threshold: int = 128) -> Image.Image:
    """Turn pixels into black/white using the simple grayscale average."""
    if isinstance(threshold, bool) or not isinstance(threshold, (int, np.integer)):
        raise TypeError("threshold must be an integer")
    if not 0 <= threshold <= 255:
        raise ValueError("threshold must be between 0 and 255")

    gray = np.asarray(grayscale_average(image))[..., 0]
    binary = np.where(gray >= threshold, 255, 0).astype(np.uint8)
    return Image.fromarray(np.stack((binary, binary, binary), axis=-1))


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
    first, second = _rgb(image_a), _rgb(image_b)
    if second.size != first.size:
        second = second.resize(first.size, resample=Image.Resampling.LANCZOS)
    return Image.blend(first, second, alpha)
