"""Connect a scaled browser canvas to the full-resolution Pillow editor."""

from base64 import b64encode
from pathlib import Path

from PIL import Image
import streamlit as st

from Images.image_draw import draw_shape, pencil_stroke, pick_color
from Images.image_io import png_bytes
from UI.image_controls import explain_operation


TOOLS = ("Pencil", "Line", "Rectangle", "Ellipse", "Eyedropper")
CANVAS_JS = Path(__file__).with_name("drawing_canvas.js").read_text(encoding="utf-8")
PREVIEW_LIMIT = (860, 470)


# Pixel position: Map the outermost preview coordinates to the original image edges.
def pixel_position(point, preview_size, image_size):
    return tuple(
        round(position * (full - 1) / (preview - 1)) if preview > 1 else (full - 1) // 2
        for position, preview, full in zip(point, preview_size, image_size)
    )


# Draw strokes: Replay pending gestures on an independent copy of the current edit.
def draw_strokes(image, strokes):
    result = image.copy()
    for tool, points, colour, thickness, filled in strokes:
        if tool == "Blank canvas":
            result = Image.new(result.mode, result.size, "white")
        elif tool == "Pencil":
            pencil_stroke(result, points[0], points[0], colour, thickness)
            for start, end in zip(points, points[1:]):
                pencil_stroke(result, start, end, colour, thickness)
        else:
            draw_shape(result, tool, points[0], points[-1], colour, thickness, filled=filled)
    return result


# Change draft: Update the pending strokes and invalidate events from the old canvas.
def change_draft(action):
    state = st.session_state
    if action == "undo" and state.strokes:
        state.strokes.pop()
    elif action == "blank":
        state.strokes.append(("Blank canvas", (), "", 0, False))
    elif action == "clear":
        state.strokes.clear()
    state.canvas_version += 1


# Canvas action: Validate one gesture, then add a stroke or sample a pixel.
def canvas_action():
    state = st.session_state
    event = state.media_canvas.action
    if (not isinstance(event, dict) or event.get("version") != state.canvas_version
            or event.get("tool") != state.drawing_tool):
        return
    points = event.get("points")
    if not isinstance(points, list) or not 1 <= len(points) <= 4096:
        return
    width, height = state.canvas_size
    if any(
        not isinstance(point, list) or len(point) != 2
        or any(type(value) is not int for value in point)
        or not (0 <= point[0] < width and 0 <= point[1] < height)
        for point in points
    ):
        return

    base = state.edited_image
    pixels = tuple(pixel_position(point, state.canvas_size, base.size) for point in points)
    tool = state.drawing_tool
    if tool == "Eyedropper":
        canvas = draw_strokes(base, state.strokes) if state.strokes else base
        red, green, blue = pick_color(canvas, *pixels[0])[:3]
        state.drawing_colour = f"#{red:02x}{green:02x}{blue:02x}"
    else:
        filled = tool in ("Rectangle", "Ellipse") and state.get("drawing_fill") == "Filled"
        state.strokes.append((tool, pixels, state.drawing_colour, state.drawing_thickness, filled))
    state.canvas_version += 1


# Drawing settings: Show shape fill only for closed shapes.
def drawing_controls():
    state = st.session_state
    tool = st.selectbox("Drawing tool", TOOLS, key="drawing_tool")
    st.color_picker("Colour", "#2354d6", key="drawing_colour")
    if tool != "Eyedropper":
        st.slider("Brush thickness (px)", 1, 50, 4, key="drawing_thickness")
    if tool in ("Rectangle", "Ellipse"):
        st.segmented_control("Shape style", ("Outline", "Filled"), default="Outline",
                             required=True, key="drawing_fill")
    with st.container(horizontal=True, gap="small"):
        st.button("Undo stroke", icon=":material/undo:", on_click=change_draft, args=("undo",),
                  disabled=not state.strokes)
        st.button("Clear drawing", icon=":material/delete_sweep:", on_click=change_draft, args=("clear",),
                  disabled=not state.strokes)
    st.button("Blank canvas", on_click=change_draft, args=("blank",), type="tertiary")
    explain_operation("Drawing")


# Show canvas: Send only a small display bitmap while retaining full-size coordinates in Python.
def show_canvas(image):
    state = st.session_state
    thumbnail = image.copy()
    thumbnail.thumbnail(PREVIEW_LIMIT)
    state.canvas_size = thumbnail.size
    tool = state.drawing_tool
    component = st.components.v2.component(
        "medialab_canvas",
        html='<div class="drawing"><img alt="" /><canvas aria-label="Drawing canvas"></canvas></div>',
        css="""
            .drawing {
                position: relative; width: 100%; overflow: hidden; border-radius: .4rem;
                background-color: #f1f4f8;
                background-image: conic-gradient(#e3e9f1 25%, #f5f7fb 0 50%, #e3e9f1 0 75%, #f5f7fb 0);
                background-size: 16px 16px;
            }
            .drawing img { display: block; width: 100%; height: auto; }
            .drawing canvas { position: absolute; inset: 0; width: 100%; height: 100%;
                cursor: crosshair; touch-action: none; }
        """,
        js=CANVAS_JS,
    )
    component(
        key="media_canvas",
        data={
            "image": "data:image/png;base64," + b64encode(png_bytes(thumbnail)).decode("ascii"),
            "width": thumbnail.width, "height": thumbnail.height,
            "tool": tool, "color": state.drawing_colour,
            "thickness": max(1, state.get("drawing_thickness", 4) * thumbnail.width / image.width),
            "filled": tool in ("Rectangle", "Ellipse") and state.get("drawing_fill") == "Filled",
            "version": state.canvas_version,
        },
        on_action_change=canvas_action,
    )
    instruction = "Click a pixel to pick its colour." if tool == "Eyedropper" else "Drag on the image to draw."
    st.caption(instruction)
