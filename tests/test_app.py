"""Exercise Streamlit navigation and the image UI with local test uploads."""

from pathlib import Path

from PIL import Image
from streamlit.testing.v1 import AppTest

from Images.image_io import png_bytes


APP = Path(__file__).resolve().parents[1] / "main.py"


def launch():
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not app.exception
    return app


def test_navigation_and_placeholders():
    app = launch()
    assert app.title[0].value == "MediaLab — Multimedia Processing Toolkit"
    for media in ("Sound", "Video", "Text"):
        app.segmented_control(key="media").set_value(media).run()
        assert not app.exception
        assert app.header[0].value == media
        assert "under development" in app.info[0].value
        assert app.button(key=f"process-{media}").proto.disabled
    app.segmented_control(key="media").set_value("Image").run()
    assert app.selectbox[1].value == "Original"


def test_upload_filter_reset_and_download():
    app = launch()
    content = png_bytes(Image.new("RGB", (11, 7), (40, 150, 200)))
    app.file_uploader[0].upload("new.png", content, "image/png").run()
    assert not app.exception and app.session_state.original_name == "new.png"
    app.selectbox[1].set_value("Negative").run()
    assert not app.exception and app.selectbox[1].value == "Negative"
    assert len(app.get("download_button")) == 1
    original = app.session_state.original_image.tobytes()
    app.button(key="reset-filter").click().run()
    assert app.selectbox[1].value == "Original"
    assert app.session_state.original_image.tobytes() == original
    app.file_uploader[0].upload("bad.png", b"wrong format", "image/png").run()
    assert not app.exception and app.error
    assert app.session_state.original_name == "new.png"
    assert app.session_state.original_image.tobytes() == original


def test_blend_and_histograms():
    app = launch()
    app.selectbox[0].set_value("Combine").run()
    assert any("Upload a second" in message.value for message in app.info)
    assert not app.get("download_button")
    app.file_uploader[1].upload(
        "second.png", png_bytes(Image.new("RGBA", (12, 4), (0, 255, 0, 99))), "image/png",
    ).run()
    assert not app.exception and len(app.get("download_button")) == 1
    app.segmented_control(key="image-tool").set_value("Histogram & adjustments").run()
    assert not app.exception
    app.slider[0].set_value(24).run()
    app.select_slider[0].set_value(128).run()
    assert any("128 bins" in item.value for item in app.caption)
    assert len(app.get("download_button")) == 1
    app.button(key="reset-histogram").click().run()
    assert not app.exception and app.slider[0].value == 0 and app.select_slider[0].value == 32


def test_drawing_blank_and_reset_preserve_source():
    app = launch()
    app.segmented_control(key="image-tool").set_value("Drawing").run()
    assert not app.exception
    before = app.session_state.drawing.tobytes()
    canvas_size = app.session_state.drawing.size
    next(b for b in app.button if b.label == "Blank canvas").click().run()
    assert not app.exception
    assert app.session_state.drawing.getpixel((canvas_size[0] // 2, canvas_size[1] // 2)) == (255, 255, 255)
    app.button(key="reset-drawing").click().run()
    assert app.session_state.drawing.tobytes() == before
    assert app.session_state.original_name == "color-study.png"
