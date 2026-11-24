"""Upload one original and preview edits in three image tools."""

from pathlib import Path

import streamlit as st

from Images import Image_filters as filters
from Images import image_histogram as histogram
from Images.image_io import UPLOAD_TYPES, download_name, png_bytes, read_image
from UI.drawing import render_drawing


SAMPLES = Path(__file__).resolve().parents[1] / "samples"
FILTERS = {
    "Colour and tone": {
        "Original": None,
        "Grayscale": filters.grayscale_average,
        "Negative": filters.negative,
        "Posterize": filters.posterize_n_levels,
        "Sepia": filters.sepia_matrix,
        "Sunset": filters.make_sunset,
        "RGB channels": filters.adjust_rgb_channels,
        "Binary threshold": filters.binary_threshold,
    },
    "Geometry": {
        "Mirror horizontally": filters.mirror_horizontal,
        "Rotate": filters.rotate_image_by_angle,
    },
    "Smoothing": {"Gaussian blur": filters.blur_image},
    "Combine": {"Blend two images": filters.blend_images},
}


# Reset tool: Refresh the widget keys for this panel and keep the original image.
def reset_tool(tool):
    state = st.session_state
    key = f"{tool}_version"
    state[key] = state.get(key, 0) + 1


# Replace original: Change previews only after a new upload or sample loads successfully.
def replace_original(name, image):
    state = st.session_state
    state.original_name = name
    state.original_image = image
    state.source_version = state.get("source_version", 0) + 1
    state.upload_error = None
    reset_tool("filter")
    reset_tool("histogram")


# Load sample: Restore the built-in sample and clear the old file picker.
def load_sample():
    name = "color-study.png"
    replace_original(name, read_image((SAMPLES / name).read_bytes()))
    st.session_state.upload_version = st.session_state.get("upload_version", 0) + 1


# Load upload: Preserve the last valid original when a new file cannot be decoded.
def load_upload(key):
    upload = st.session_state.get(key)
    if upload is None:
        return
    try:
        replace_original(upload.name, read_image(upload.getvalue()))
    except ValueError as exc:
        st.session_state.upload_error = str(exc)


# Preview: Show an image within a bounded size while keeping exports at full resolution.
def preview(image, title):
    with st.container(border=True):
        st.markdown(f"**{title}**")
        thumbnail = image.copy()
        thumbnail.thumbnail((780, 480))
        st.image(thumbnail, output_format="PNG", alt=f"{title} image")
        st.caption(f"{image.width} × {image.height} px")


# Download: Send an independent PNG copy of the current result.
def download(image, operation, *, label="Download PNG", key=None):
    st.download_button(
        label, png_bytes(image), download_name(st.session_state.original_name, operation),
        mime="image/png", on_click="ignore", key=key,
    )


# Filter settings: Collect only the controls required by the selected operation.
def filter_settings(operation, key):
    if operation == "Posterize":
        return (st.slider("Levels per channel", 2, 32, 6, key=f"{key}-levels"),)
    if operation == "Sunset":
        return (st.slider("Green and blue multiplier", 0.0, 1.0, 0.7, 0.05, key=f"{key}-sunset"),)
    if operation == "RGB channels":
        return tuple(
            st.slider(f"{channel} (%)", 0, 200, 100, 5, key=f"{key}-{channel}")
            for channel in ("Red", "Green", "Blue")
        )
    if operation == "Binary threshold":
        return (st.slider("Threshold", 0, 255, 128, key=f"{key}-threshold"),)
    if operation == "Rotate":
        return (st.slider("Angle (° counterclockwise)", -180, 180, 0, key=f"{key}-angle"),)
    if operation == "Gaussian blur":
        return (st.slider("Blur radius (px)", 0.0, 20.0, 2.0, 0.5, key=f"{key}-blur"),)
    if operation == "Blend two images":
        second = st.file_uploader("Upload second image", type=UPLOAD_TYPES, key=f"{key}-blend")
        weight = st.slider("Second image (%)", 0, 100, 50, key=f"{key}-weight") / 100
        if second is None:
            return None
        return (read_image(second.getvalue()), weight)
    return ()


# Render filters: Apply an effect to the original and offer a side-by-side comparison.
def render_filters(original, controls, result):
    version = f"filter-{st.session_state.filter_version}"
    processed = None
    error = None
    with controls:
        st.markdown("**Filter settings**")
        group = st.selectbox("Category", list(FILTERS), key=f"{version}-category")
        operation = st.selectbox("Filter", list(FILTERS[group]), key=f"{version}-{group}")
        try:
            args = filter_settings(operation, version)
            if args is not None:
                function = FILTERS[group][operation]
                if function is None:
                    processed = original
                else:
                    with st.spinner("Applying filter…"):
                        processed = function(original, *args)
        except ValueError as exc:
            error = str(exc)
        reset, export = st.columns(2)
        reset.button("Reset", on_click=reset_tool, args=("filter",), key="reset-filter")
        if processed is not None:
            with export:
                download(processed, operation, key="download-filter")

    with result:
        before, after = st.columns(2)
        with before:
            preview(original, "Original")
        with after:
            if processed is not None:
                preview(processed, "Processed")
                st.caption("Preview is current.")
            elif error is not None:
                st.error(error)
            else:
                st.info("Upload a second image to preview the blend.")
                st.caption("The second image is resized to match the original.")


# Render adjustments: Use the histogram module for brightness, contrast and counts.
def render_adjustments(original, controls, result):
    version = f"histogram-{st.session_state.histogram_version}"
    with controls:
        st.markdown("**Adjustment settings**")
        amount = st.slider("Brightness offset", -255, 255, 0, key=f"{version}-brightness")
        factor = st.slider("Contrast multiplier", 0.0, 3.0, 1.0, 0.05, key=f"{version}-contrast")
        bins = st.select_slider(
            "Histogram bins", options=[8, 16, 32, 64, 128, 256], value=32, key=f"{version}-bins",
        )
        with st.spinner("Updating preview…"):
            processed = histogram.adjust_contrast(histogram.adjust_brightness(original, amount), factor)
        reset, export = st.columns(2)
        reset.button("Reset", on_click=reset_tool, args=("histogram",), key="reset-histogram")
        with export:
            download(processed, "adjusted", key="download-histogram")

    with result:
        preview(processed, "Processed")
        figures = [
            histogram.plot_histogram(image, bins, title)
            for image, title in ((original, "Original histogram"), (processed, "Processed histogram"))
        ]
        maximum = max(figure.axes[0].get_ylim()[1] for figure in figures)
        for column, figure in zip(st.columns(2), figures):
            figure.axes[0].set_ylim(0, maximum)
            column.pyplot(figure, alt=figure.axes[0].get_title())
        st.caption(f"{bins} bins · {original.width * original.height:,} pixels in each histogram.")


# Render image workbench: Keep a shared original while users switch or reset tools.
def render_image_workbench():
    state = st.session_state
    if "original_image" not in state:
        load_sample()
    tool = st.segmented_control(
        "Image tool", ["Filters", "Histogram & adjustments", "Drawing"],
        default="Filters", required=True, key="image-tool", label_visibility="collapsed",
    )
    left, right = st.columns([1, 2.55], gap="medium")
    with left:
        with st.container(border=True):
            st.markdown("**Original image**")
            key = f"upload-{state.upload_version}"
            st.file_uploader(
                "Upload image", type=UPLOAD_TYPES, key=key, on_change=load_upload, args=(key,),
            )
            st.button("Use sample image", on_click=load_sample)
            st.caption(state.original_name)
            if state.upload_error:
                st.error(state.upload_error)
        controls = st.container(border=True)
    if tool == "Filters":
        render_filters(state.original_image, controls, right)
    elif tool == "Histogram & adjustments":
        render_adjustments(state.original_image, controls, right)
    else:
        render_drawing(controls, right)
