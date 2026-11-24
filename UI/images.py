"""Manage the original, applied edits and the current temporary preview."""

from io import BytesIO
from pathlib import Path

import streamlit as st

from Images import image_histogram as histogram
from Images.image_io import UPLOAD_TYPES, download_name, png_bytes, read_image
from UI.drawing import draw_strokes, drawing_controls, show_canvas
from UI.image_controls import (
    ADJUSTMENTS, BINS, FILTERS, TRANSFORMS, adjustment_preview, combination_preview,
    explain_operation, filter_preview, tone_preview, transform_preview,
)


SAMPLES = Path(__file__).resolve().parents[1] / "samples"
TOOLS = ("Filters", "Adjustments", "Transformations", "Combination", "Drawing", "Histogram")
HISTORY_LIMIT = 5
HISTORY_BYTES = 96 * 1024 * 1024


# Reset preview: Restore neutral controls and keep or clear the uncommitted drawing.
def reset_preview(clear_drawing=False):
    state = st.session_state
    state.tool_version = state.get("tool_version", 0) + 1
    if clear_drawing:
        state.strokes = []
        state.canvas_version = state.get("canvas_version", 0) + 1


# Replace original: Start an independent editing session only after a valid open.
def replace_original(name, image):
    state = st.session_state
    state.original_name = name
    state.original_image = image
    state.edited_image = image
    state.saved_png = None
    state.history = []
    state.upload_error = None
    reset_preview(clear_drawing=True)


# Load sample: Open the included sample and clear the uploader selection.
def load_sample():
    name = "color-study.png"
    replace_original(name, read_image((SAMPLES / name).read_bytes()))
    st.session_state.upload_version = st.session_state.get("upload_version", 0) + 1


# Load upload: Keep editing the previous image if the new file is invalid.
def load_upload(key):
    state = st.session_state
    upload = state.get(key)
    state.upload_error = None
    if upload is None:
        return
    try:
        replace_original(upload.name, read_image(upload.getvalue()))
    except ValueError as exc:
        state.upload_error = str(exc)


# Commit edit: Store the previous version and make the preview the current edited image.
def commit_edit(preview):
    state = st.session_state
    state.history.append(state.edited_image)
    while len(state.history) > 1 and (
        len(state.history) > HISTORY_LIMIT
        or sum(image.width * image.height * len(image.getbands()) for image in state.history) > HISTORY_BYTES
    ):
        state.history.pop(0)
    state.edited_image = preview
    state.saved_png = None
    reset_preview(clear_drawing=True)


# Undo edit: Restore the last applied version and start a clean preview.
def undo_edit():
    state = st.session_state
    state.edited_image = state.history.pop()
    state.saved_png = None
    reset_preview(clear_drawing=True)


# Restore original: Return to the original with the previous edit available through Undo.
def restore_original():
    commit_edit(st.session_state.original_image)


# Show image: Use a contained thumbnail in the workspace and display the true image size.
def show_image(image, title):
    st.markdown(f"**{title}**")
    thumbnail = image.copy()
    thumbnail.thumbnail((860, 470))
    st.image(thumbnail, output_format="PNG", alt=f"{title} image", width="stretch")
    st.caption(f"{image.width} × {image.height} px")


# Show histograms: Plot the original and output using a common comparison scale.
def show_histograms(original, edited, bins):
    images = (original, edited)
    counts = [histogram.binned_histogram(image, bins) for image in images]
    maximum = max(1, *(max(group) for group in counts)) * 1.08
    with st.container(key="histogram-plots"):
        for column, title, image, group in zip(
            st.columns(2), ("Original histogram", "Edited histogram"), images, counts,
        ):
            figure = histogram.plot_histogram(image, bins, title, counts=group)
            figure.axes[0].set_ylim(0, maximum)
            with BytesIO() as plot:
                figure.savefig(plot, format="png", dpi=116)
                column.image(plot.getvalue(), width="stretch", alt=title)
            column.caption(f"{sum(group):,} pixels counted")
    st.caption("Fully transparent pixels are excluded.")


# Tool preview: Collect only the chosen tool's controls and calculate from the applied image.
def tool_preview(tool, image):
    state = st.session_state
    key = f"{tool}-{state.tool_version}"
    if tool == "Drawing":
        drawing_controls()
        return draw_strokes(image, state.strokes) if state.strokes else None, None
    if tool == "Histogram":
        bins = st.select_slider("Histogram bins", BINS, value=32, key="histogram-bins")
        result = tone_preview(image, key)
        explain_operation("Histogram", "Brightness", "Contrast")
        return result, bins
    if tool == "Combination":
        result = combination_preview(image, key)
        explain_operation("Blend two images")
        return result, None

    options, renderer = {
        "Filters": (FILTERS, filter_preview),
        "Adjustments": (ADJUSTMENTS, adjustment_preview),
        "Transformations": (TRANSFORMS, transform_preview),
    }[tool]
    label = {"Filters": "Filter", "Adjustments": "Adjustment", "Transformations": "Transformation"}[tool]
    operation = st.selectbox(label, options, index=None, placeholder=f"Choose a {label.lower()}", key=key)
    if operation is None:
        return None, None
    result = renderer(image, operation, key)
    details = (operation, "Filter intensity") if tool == "Filters" and operation != "Sunset" else (operation,)
    explain_operation(*details)
    return result, None


# Open image: Show upload and sample choices without consuming permanent workspace height.
def open_image():
    state = st.session_state
    with st.popover("Open image", icon=":material/folder_open:"):
        key = f"upload-{state.upload_version}"
        st.file_uploader("Upload image", type=UPLOAD_TYPES, key=key, on_change=load_upload, args=(key,))
        st.button("Use sample image", on_click=load_sample)
        st.caption("Opening an image starts a new edit. Save your current image first if you need it.")
    st.text(state.original_name)


# Edit actions: Apply the preview, recover prior versions and save the last applied image.
def edit_actions(preview, tool):
    state = st.session_state
    if st.button("Apply", icon=":material/check:", key="apply-image", type="primary", disabled=preview is None):
        commit_edit(preview)
        st.rerun()
    st.button("Undo", icon=":material/undo:", key="undo-image", disabled=not state.history, on_click=undo_edit)
    if tool != "Drawing":
        st.button("Reset adjustment", icon=":material/restart_alt:", key="reset-adjustment",
                  on_click=reset_preview)
    st.button("Restore original", key="restore-original", disabled=state.edited_image is state.original_image,
              on_click=restore_original, help="Return to the opened image. Undo can bring the edit back.")
    if state.saved_png is None:
        state.saved_png = png_bytes(state.edited_image)
    st.download_button(
        "Save PNG", state.saved_png, download_name(state.original_name, "edited"),
        mime="image/png", on_click="ignore", icon=":material/download:", key="save-image",
        disabled=preview is not None,
        help="Apply the preview or reset it before saving at full resolution.",
    )


# Image workbench: Keep the original beside the temporary preview or last applied image.
def render_image_workbench():
    state = st.session_state
    if "original_image" not in state:
        load_sample()
    with st.container(horizontal=True, key="media-toolbar", vertical_alignment="center"):
        open_image()
        actions = st.container(horizontal=True, vertical_alignment="center")
    if state.upload_error:
        st.error(f"{state.upload_error} Your current image is still open.")
    tool = st.segmented_control("Image tools", TOOLS, default="Filters", required=True,
                                key="image-tool", label_visibility="collapsed", wrap=True)
    toolbox, workspace = st.columns([1, 3.25], gap="medium")
    with toolbox:
        with st.container(key="image-toolbox"):
            try:
                preview, bins = tool_preview(tool, state.edited_image)
            except ValueError as exc:
                st.error(str(exc))
                preview, bins = None, None
    with actions:
        edit_actions(preview, tool)

    edited = preview if preview is not None else state.edited_image
    with workspace:
        if preview is not None:
            st.caption("Preview only · Apply to keep these changes.")
        elif state.edited_image is state.original_image:
            st.caption("Original ready to edit.")
        else:
            st.caption("Edit applied · Ready to save.")
        with st.container(key="histogram-preview" if bins is not None else "image-preview"):
            left, right = st.columns(2)
            with left:
                show_image(state.original_image, "Original")
            with right:
                if tool == "Drawing":
                    st.markdown("**Drawing preview**")
                    show_canvas(edited)
                    st.caption(f"{edited.width} × {edited.height} px")
                else:
                    show_image(edited, "Preview" if preview is not None else "Edited")
        if bins is not None:
            show_histograms(state.original_image, edited, bins)
