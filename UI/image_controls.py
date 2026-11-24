"""Friendly editor controls with explicit mappings to the image algorithms."""

import streamlit as st

from Images import Image_filters as filters
from Images import image_histogram as histogram
from Images.image_io import UPLOAD_TYPES, read_image


FILTERS = ("Grayscale", "Invert Colours", "Sepia", "Sunset", "Posterization", "Black and White")
ADJUSTMENTS = ("Brightness", "Contrast", "Colour balance", "Blur")
TRANSFORMS = ("Rotate", "Flip horizontally", "Flip vertically")
BINS = (8, 16, 32, 64, 128, 256)
MAX_EDIT_PIXELS = 24_000_000

HOW_IT_WORKS = {
    "Grayscale": "Each pixel gets the same value in its three colour channels. The value is the whole-number average of red, green and blue. This demonstrates a point operation on RGB data.",
    "Invert Colours": "Each colour channel becomes 255 minus its value. Black becomes white and nearby colours change independently. This is the course's negative effect.",
    "Sepia": "Each output channel is a weighted sum of the three input channels, rounded and clipped to 0–255. The RGB matrix gives the picture a warm tint.",
    "Sunset": "The red channel stays fixed. Green and blue are multiplied by 1 minus the intensity divided by 100. At 0% the picture is unchanged.",
    "Posterization": "Each channel is rounded to the nearest of the selected evenly spaced levels from 0 to 255. Fewer levels create a flatter look and illustrate quantization.",
    "Black and White": "A pixel becomes white if its average RGB value reaches the cutoff, and black otherwise. A higher cutoff leaves fewer white pixels. This is binary thresholding.",
    "Filter intensity": "The result mixes the original colours of this edit with the filtered colours. At 0% the filter has no effect. At 100% you see the full filter. Transparency is kept.",
    "Brightness": "Brightness adds a fixed offset from −128 to +128 to each colour value. 50 adds zero. Values outside 0–255 are clipped.",
    "Contrast": "New value = mean + factor × (value − mean). The mean uses visible pixels. 50 gives a factor of 1, and 100 gives 2. Strong contrast can lose detail to clipping.",
    "Colour balance": "Each channel is multiplied by its own factor from 0 to 2. 50 gives a factor of 1. Values above 255 are clipped. The alpha channel stays intact.",
    "Blur": "A Gaussian blur combines neighbouring pixels. 0 keeps the image and 100 uses a 20-pixel radius. Opacity is used when averaging to avoid colour bleeding from invisible pixels.",
    "Rotate": "Pillow maps each destination position back to the source and interpolates between nearby pixels. The canvas expands to fit. New corners are transparent on images with alpha and white on opaque images.",
    "Flip horizontally": "For width W, column x moves to W − 1 − x. The rows stay in the same order.",
    "Flip vertically": "For height H, row y moves to H − 1 − y. The columns stay in the same order.",
    "Blend two images": "The result is (1 − weight) × edited image + weight × second image. The second image is resized to match. Transparent pixels contribute in proportion to their opacity.",
    "Histogram": "A histogram counts pixels by brightness, then groups neighbouring values into bins. Both charts use the same axes. Fully transparent pixels are excluded. Every pixel with nonzero opacity counts once.",
    "Drawing": "Pillow draws in full-resolution pixel coordinates. The on-screen canvas is a scaled view. The eyedropper reads the colour at a pixel in the current preview.",
}


# Brightness offset: Center the 0–100 slider at zero and bound its effect.
def brightness_offset(value):
    return round((value - 50) * 128 / 50)


# Channel gain: Map the center of the slider to an unchanged channel.
def channel_gain(value):
    return value / 50


# Threshold: Convert a percentage into an inclusive 8-bit cutoff.
def intensity_cutoff(value):
    return round(value * 255 / 100)


# Filter preview: Read settings for the chosen filter and build its result from the edited image.
def filter_preview(image, operation, key):
    if operation == "Sunset":
        value = st.slider("Sunset intensity (%)", 0, 100, 0, key=f"{key}-sunset",
                          help="Higher values give the picture a warmer tint.")
        return filters.make_sunset(image, 1 - value / 100) if value else None

    effect = {
        "Grayscale": filters.grayscale_average,
        "Invert Colours": filters.negative,
        "Sepia": filters.sepia_matrix,
        "Posterization": filters.posterize_n_levels,
        "Black and White": filters.binary_threshold,
    }
    args = ()
    if operation == "Posterization":
        args = (st.select_slider("Colour levels", (2, 4, 8, 16, 32),
                                 value=8, key=f"{key}-levels",
                                 help="Fewer levels give a flatter look."),)
    elif operation == "Black and White":
        value = st.slider("Black and white cutoff (%)", 0, 100, 50, key=f"{key}-cutoff",
                          help="Move right for more black areas.")
        args = (intensity_cutoff(value),)
    strength = st.slider("Filter intensity (%)", 0, 100, 100, key=f"{key}-intensity",
                         help="0% keeps the current image. 100% shows the full filter.")
    if strength == 0:
        return None
    processed = effect[operation](image, *args)
    return processed if strength == 100 else filters.blend_images(image, processed, strength / 100)


# Tone preview: Apply brightness first, then contrast, with 50 as the neutral setting.
def tone_preview(image, key, operation=None):
    brightness = contrast = 50
    if operation in (None, "Brightness"):
        brightness = st.slider("Brightness", 0, 100, 50, key=f"{key}-brightness",
                               help="Move left for darker or right for brighter. 50 keeps it unchanged.")
    if operation in (None, "Contrast"):
        contrast = st.slider("Contrast", 0, 100, 50, key=f"{key}-contrast",
                             help="Move right to make bright and dark areas more distinct. 50 keeps it unchanged.")
    if brightness == contrast == 50:
        return None
    result = histogram.adjust_brightness(image, brightness_offset(brightness)) if brightness != 50 else image
    return histogram.adjust_contrast(result, channel_gain(contrast)) if contrast != 50 else result


# Adjustment preview: Read the controls for one adjustment and map them to image units.
def adjustment_preview(image, operation, key):
    if operation in ("Brightness", "Contrast"):
        return tone_preview(image, key, operation)
    if operation == "Blur":
        value = st.slider("Blur strength", 0, 100, 0, key=f"{key}-blur",
                          help="Move right to soften more detail.")
        return filters.blur_image(image, value / 5) if value else None
    channels = [
        st.slider(channel, 0, 100, 50, key=f"{key}-{channel.lower()}",
                  help=f"Move right for more {channel.lower()}. 50 keeps it unchanged.")
        for channel in ("Red", "Green", "Blue")
    ]
    return filters.adjust_rgb_channels(image, *(value * 2 for value in channels)) if any(
        value != 50 for value in channels
    ) else None


# Transform preview: Keep pixel dimensions for flips and rotate by the requested clockwise angle.
def transform_preview(image, operation, key):
    if operation == "Rotate":
        angle = st.slider("Clockwise turn (°)", 0, 360, 0, step=1, key=f"{key}-angle")
        return filters.rotate_image_by_angle(image, -angle, max_pixels=MAX_EDIT_PIXELS) if angle % 360 else None
    return filters.mirror_horizontal(image) if operation == "Flip horizontally" else filters.mirror_vertical(image)


# Combination preview: Use a friendly blend percentage and validate only the second image.
def combination_preview(image, key):
    uploaded = st.file_uploader("Open second image", type=UPLOAD_TYPES, key=f"{key}-second")
    if uploaded is None:
        return None
    value = st.slider("Second image (%)", 0, 100, 50, key=f"{key}-blend",
                      help="Move right to show more of the second image.")
    if value == 0:
        return None
    return filters.blend_images(image, read_image(uploaded.getvalue()), value / 100)


# Explain operation: Keep optional CPIT-380 theory out of the main editing workflow.
def explain_operation(*operations):
    with st.expander("How It Works"):
        for operation in operations:
            st.markdown(f"**{operation}**")
            st.write(HOW_IT_WORKS[operation])
        st.caption("CPIT-380 · Image processing")
