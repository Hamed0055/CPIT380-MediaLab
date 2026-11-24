"""Display a pointer canvas and pass completed strokes to Pillow."""

from base64 import b64encode
from pathlib import Path

from PIL import Image, ImageOps
import streamlit as st

from Images.image_draw import HEIGHT, WIDTH, draw_shape, pencil_stroke, pick_color
from Images.image_io import download_name, png_bytes


TOOLS = ("Pencil", "Line", "Rectangle", "Ellipse", "Eyedropper")
CANVAS_FILE = Path(__file__).with_name("drawing_canvas.js")


# Fit canvas: Centre a copy of the original on the drawing tool's white canvas.
def fit_canvas(original):
    canvas = Image.new("RGB", (WIDTH, HEIGHT), "white")
    if original is None:
        return canvas
    fitted = ImageOps.contain(original.convert("RGBA"), canvas.size)
    origin = ((WIDTH - fitted.width) // 2, (HEIGHT - fitted.height) // 2)
    canvas.paste(fitted, origin, fitted)
    return canvas


# Edit canvas: Reuse the drawing module to apply pointer positions to a new bitmap.
def edit_canvas(image, tool, points, color, thickness):
    result = image.copy()
    if tool == "Pencil":
        pencil_stroke(result, points[0], points[0], color, thickness)
        for start, end in zip(points, points[1:]):
            pencil_stroke(result, start, end, color, thickness)
    else:
        draw_shape(result, tool, points[0], points[-1], color, thickness)
    return result


# Reset canvas: Restore the source or start a blank canvas while retaining the original.
def reset_canvas(blank=False):
    state = st.session_state
    state.drawing = fit_canvas(None if blank else state.original_image)
    state.drawing_source = state.source_version
    state.drawing_version = state.get("drawing_version", 0) + 1
    state.drawing_png = png_bytes(state.drawing)


# Canvas action: Commit one stroke or use its first point to sample a color.
def canvas_action():
    state = st.session_state
    event = state.media_canvas.action
    if not isinstance(event, dict) or event.get("version") != state.drawing_version:
        return
    points = event.get("points")
    if not isinstance(points, list) or not 1 <= len(points) <= 4096:
        return
    if any(
        not isinstance(point, list)
        or len(point) != 2
        or any(type(value) is not int for value in point)
        or not (0 <= point[0] < WIDTH and 0 <= point[1] < HEIGHT)
        for point in points
    ):
        return

    tool = state.drawing_tool
    if tool == "Eyedropper":
        red, green, blue = pick_color(state.drawing, *points[0])
        state.drawing_color = f"#{red:02x}{green:02x}{blue:02x}"
    else:
        state.drawing = edit_canvas(
            state.drawing, tool, points, state.drawing_color, state.drawing_thickness,
        )
        state.drawing_png = png_bytes(state.drawing)
    state.drawing_version += 1


# Render drawing: Show the current bitmap, controls, and an editable preview layer.
def render_drawing(controls, result):
    state = st.session_state
    if state.get("drawing_source") != state.source_version:
        reset_canvas()
    with controls:
        st.markdown("**Drawing settings**")
        tool = st.selectbox("Tool", TOOLS, key="drawing_tool")
        color = st.color_picker("Colour", "#2354d6", key="drawing_color")
        thickness = st.slider("Brush thickness (px)", 1, 25, 4, key="drawing_thickness")
        reset, blank = st.columns(2)
        reset.button("Reset", on_click=reset_canvas, key="reset-drawing")
        blank.button("Blank canvas", on_click=reset_canvas, args=(True,))
        st.download_button(
            "Save PNG", state.drawing_png, download_name(state.original_name, "drawing"),
            mime="image/png", on_click="ignore",
        )

    with result:
        component = st.components.v2.component(
            "medialab_canvas",
            html='<div class="drawing"><img alt="" /><canvas aria-label="Drawing canvas"></canvas></div>',
            css="""
                .drawing {
                    position: relative; width: 100%; max-width: 800px; overflow: hidden;
                    border: 1px solid #a9b5cd; border-radius: 7px; background: white;
                }
                .drawing img { display: block; width: 100%; }
                .drawing canvas { position: absolute; inset: 0; width: 100%; height: 100%;
                    cursor: crosshair; touch-action: none; }
            """,
            js=CANVAS_FILE.read_text(encoding="utf-8"),
        )
        component(
            key="media_canvas",
            data={
                "image": "data:image/png;base64," + b64encode(state.drawing_png).decode("ascii"),
                "width": WIDTH, "height": HEIGHT, "tool": tool, "color": color,
                "thickness": thickness, "version": state.drawing_version,
            },
            on_action_change=canvas_action,
        )
        instruction = "Click a pixel to pick its colour." if tool == "Eyedropper" else "Drag on the canvas to draw."
        st.caption(f"{instruction} Canvas exports at {WIDTH} × {HEIGHT} px.")
