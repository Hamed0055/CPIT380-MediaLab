"""Exercise the local editing workflow through the Streamlit widgets."""

from pathlib import Path

from PIL import Image
from streamlit.testing.v1 import AppTest

from Images.image_io import png_bytes


APP = Path(__file__).resolve().parents[1] / "main.py"


def launch():
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not app.exception and not app.warning
    return app


def tool(app, name):
    app.segmented_control(key="image-tool").set_value(name).run()
    assert not app.exception


def open_image(app, image, name="example.png"):
    app.file_uploader[0].upload(name, png_bytes(image), "image/png").run()
    assert not app.exception


def apply(app):
    button = app.button(key="apply-image")
    assert not button.proto.disabled
    button.click().run()
    assert not app.exception


def test_navigation_and_open_menus():
    app = launch()
    assert app.title[0].value == "MediaLab"
    for media in ("Audio", "Video", "Text"):
        app.segmented_control(key="media").set_value(media).run()
        assert not app.exception
        assert all("Under Development" not in item.value for item in app.info)
        if media != "Video" or not app.warning:
            assert not app.file_uploader[0].proto.disabled


def test_live_preview_sequential_apply_undo_and_restore():
    app = launch()
    open_image(app, Image.new("RGBA", (12, 5), (50, 100, 150, 120)))
    app.selectbox[0].set_value("Invert Colours").run()
    app.slider[0].set_value(50).run()
    app.slider[0].set_value(100).run()
    assert app.session_state.edited_image.getpixel((0, 0)) == (50, 100, 150, 120)
    assert not app.session_state.history
    apply(app)
    assert app.session_state.edited_image.getpixel((0, 0)) == (205, 155, 105, 120)
    assert app.button(key="apply-image").proto.disabled

    tool(app, "Adjustments")
    app.selectbox[0].set_value("Brightness").run()
    assert app.slider[0].value == 50
    app.slider[0].set_value(75).run()
    apply(app)
    assert app.session_state.edited_image.getpixel((0, 0)) == (255, 219, 169, 120)
    assert app.session_state.original_image.getpixel((0, 0)) == (50, 100, 150, 120)

    app.button(key="undo-image").click().run()
    assert app.session_state.edited_image.getpixel((0, 0)) == (205, 155, 105, 120)
    app.button(key="restore-original").click().run()
    assert app.session_state.edited_image.getpixel((0, 0)) == (50, 100, 150, 120)
    app.button(key="undo-image").click().run()
    assert app.session_state.edited_image.getpixel((0, 0)) == (205, 155, 105, 120)


def test_reset_and_invalid_upload_keep_applied_image():
    app = launch()
    open_image(app, Image.new("RGB", (11, 7), (40, 80, 200)))
    app.selectbox[0].set_value("Grayscale").run()
    apply(app)
    applied = app.session_state.edited_image.tobytes()
    app.selectbox[0].set_value("Sepia").run()
    app.button(key="reset-adjustment").click().run()
    assert app.selectbox[0].value is None
    assert app.session_state.edited_image.tobytes() == applied
    app.file_uploader[0].upload("broken.png", b"bad-data", "image/png").run()
    assert not app.exception and "still open" in app.error[0].value
    assert app.session_state.original_name == "example.png"
    assert app.session_state.edited_image.tobytes() == applied


def test_blend_controls_and_histogram_keep_current_version():
    app = launch()
    open_image(app, Image.new("RGB", (12, 5), (40, 120, 140)))
    tool(app, "Combination")
    assert app.button(key="apply-image").proto.disabled
    app.file_uploader[1].upload(
        "second.png", png_bytes(Image.new("RGB", (3, 8), (100, 20, 220))), "image/png",
    ).run()
    assert app.slider[0].value == 50
    apply(app)
    assert app.session_state.edited_image.getpixel((0, 0)) == (70, 70, 180)
    tool(app, "Histogram")
    assert all(s.value == 50 for s in app.slider)
    app.select_slider[0].set_value(128).run()
    assert [item.value for item in app.caption].count("60 pixels counted") == 2
    app.slider[0].set_value(100).run()
    assert app.session_state.edited_image.getpixel((0, 0)) == (70, 70, 180)
    apply(app)
    assert app.session_state.edited_image.getpixel((0, 0)) == (198, 198, 255)
    assert app.select_slider[0].value == 128


def test_drawing_draft_survives_switches_and_applies_at_source_size():
    app = launch()
    open_image(app, Image.new("RGB", (1300, 900), "red"))
    tool(app, "Drawing")
    next(button for button in app.button if button.label == "Blank canvas").click().run()
    assert not app.exception and app.session_state.strokes
    assert app.session_state.edited_image.getpixel((0, 0)) == (255, 0, 0)
    tool(app, "Filters")
    tool(app, "Drawing")
    apply(app)
    result = app.session_state.edited_image
    assert result.size == (1300, 900)
    assert result.getpixel((0, 0)) == (255, 255, 255)
    assert not app.session_state.strokes
    app.button(key="undo-image").click().run()
    assert app.session_state.edited_image.getpixel((0, 0)) == (255, 0, 0)


def test_audio_reverse_apply_and_undo():
    from Sound import sound_effects

    app = launch()
    app.segmented_control(key="media").set_value("Audio").run()
    payload = (APP.parent / "samples" / "sample-tone.wav").read_bytes()
    app.file_uploader[0].upload("test.wav", payload, "audio/wav").run()
    source = sound_effects.read_wav(payload)
    app.selectbox[0].set_value("Reverse").run()
    assert not app.exception
    assert app.session_state["media-Audio"]["original"].samples.tolist() == source.samples.tolist()
    next(button for button in app.button if button.label == "Apply").click().run()
    assert not app.exception
    state = app.session_state["media-Audio"]
    assert state["edited"].samples.tolist() == source.samples[::-1].tolist()
    next(button for button in app.button if button.label == "Undo").click().run()
    assert not app.exception
    assert app.session_state["media-Audio"]["edited"] is state["original"]


def test_text_edit_format_and_preserve_session():
    app = launch()
    app.segmented_control(key="media").set_value("Text").run()
    app.file_uploader[0].upload("test.txt", b"moon & sea", "text/plain").run()
    app.selectbox[0].set_value("Uppercase").run()
    next(button for button in app.button if button.label == "Apply").click().run()
    assert not app.exception
    assert app.session_state["media-Text"]["edited"][0] == "MOON & SEA"
    app.selectbox[0].set_value("Format as HTML").run()
    next(box for box in app.checkbox if box.label == "Bold").set_value(True).run()
    next(button for button in app.button if button.label == "Apply").click().run()
    assert not app.exception and app.session_state["media-Text"]["edited"][1]["bold"]
    app.segmented_control(key="media").set_value("Image").run()
    app.segmented_control(key="media").set_value("Text").run()
    assert not app.exception and app.session_state["media-Text"]["original"][0] == "moon & sea"
