"""Check media formats, sample arithmetic, literal text, and real MP4 exports."""

from pathlib import Path

import numpy as np
import pytest

from Sound import sound_effects as sound
from Text import text_operations as text
from Video import video_effects as video


SAMPLES = Path(__file__).resolve().parents[1] / "samples"


@pytest.mark.parametrize("width", [1, 2, 3, 4])
def test_pcm_roundtrip_and_gain_clips(width):
    limit = 1 << (8 * width - 1)
    source = np.array([[-limit, limit - 1], [0, 1], [40, -40]], dtype=np.int32)
    clip = sound.Sound(source, 8000, width)
    restored = sound.read_wav(sound.wav_bytes(clip))
    np.testing.assert_array_equal(restored.samples, source)
    assert (restored.rate, restored.channels, restored.width) == (8000, 2, width)
    np.testing.assert_array_equal(sound.adjust_volume(clip, 1).samples, source)
    assert sound.adjust_volume(clip, 2).samples[0].tolist() == [-limit, limit - 1]
    np.testing.assert_array_equal(sound.reverse_sound(clip).samples, source[::-1])


def test_wav_effect_timelines_and_invalid_inputs(monkeypatch):
    clip = sound.Sound(np.array([[800, -800], [200, -200], [0, 0]], np.int32), 1000, 2)
    other = sound.Sound(np.array([[200, 200]], np.int32), 1000, 2)
    assert sound.add_echo(clip, 0.001, 0.5).samples.tolist() == [
        [800, -800], [600, -600], [100, -100], [0, 0],
    ]
    assert sound.trim_sound(clip, .001, .003).samples.tolist() == [[200, -200], [0, 0]]
    assert sound.splice_sounds(clip, other).samples[-1].tolist() == [200, 200]
    assert sound.blend_sounds(clip, other, .5).samples.tolist() == [[500, -300], [100, -100], [0, 0]]
    assert sound.blend_sounds(clip, other, 1) is other
    with pytest.raises(ValueError, match="same sample rate"):
        sound.splice_sounds(clip, sound.Sound(other.samples, 8000, 2))
    with pytest.raises(ValueError, match="after"):
        sound.trim_sound(clip, .003, .001)
    with pytest.raises(ValueError, match="readable"):
        sound.read_wav(b"bad input")
    with pytest.raises(ValueError, match="incomplete"):
        sound.read_wav(sound.wav_bytes(clip)[:-1])
    monkeypatch.setattr(sound, "MAX_BYTES", len(sound.wav_bytes(clip)))
    with pytest.raises(ValueError, match="20 MB"):
        sound.splice_sounds(clip, other)
    with pytest.raises(ValueError, match="20 MB"):
        sound.add_echo(clip, .001, .5)


def test_text_cleaning_unicode_and_literal_replacement():
    value = text.read_text(b"\xef\xbb\xbf" + "caf\u00e9   moon\r\n\r\n\r\n &  sea".encode())
    assert text.clean_whitespace(value) == "caf\u00e9 moon\n\n& sea"
    assert text.find_replace(value, "moon", "[.*]") == value.replace("moon", "[.*]")
    assert text.uppercase_text("caf\u00e9") == "CAF\u00c9"
    assert text.lowercase_text("CAF\u00c9") == "caf\u00e9"
    assert text.titlecase_text("above the sea") == "Above The Sea"
    assert text.count_words("caf\u00e9  sky\nmoon") == 3
    assert text.count_characters("caf\u00e9") == 4
    for payload in [b"\xff", b"abc\x00def"]:
        with pytest.raises(ValueError):
            text.read_text(payload)
    with pytest.raises(ValueError, match="find"):
        text.find_replace("abc", "", "x")


def test_html_is_standalone_escaped_and_style_is_validated():
    value = "<script>alert('hello')</script> & hello\nnew line\n\nsecond paragraph"
    html = text.generate_html_document(value, {"font": "Serif", "bold": True, "alignment": "center"})
    assert html.startswith("<!doctype html>")
    assert "&lt;script&gt;" in html and "<script>" not in html
    assert "&amp;" in html and "<br>new line" in html
    assert html.count("<p ") == 2 and "font-weight:bold" in html
    assert "text-align:center" in html
    with pytest.raises(ValueError, match="formatting"):
        text.format_html("a", {"colour": '#ffffff";position:fixed'})


@pytest.mark.skipif(not video.video_tools_available(), reason="needs local FFmpeg and ffprobe")
@pytest.mark.parametrize("effect,value", [("Grayscale", None), ("Invert Colours", None),
                                          ("Posterization", 4), ("Brightness", 32), ("Trim", None)])
def test_real_mp4_export_keeps_picture_audio_and_expected_duration(effect, value):
    source = (SAMPLES / "sample-video.mp4").read_bytes()
    info = video.get_video_info(source)
    start, end = (0.5, 1.5) if effect == "Trim" else (0, info.duration)
    preview = video.preview_frame(source, info, effect, value, start=start)
    updates = []
    payload, edited = video.process_video(source, info, effect, value, start=start, end=end,
                                          progress=updates.append)
    assert (edited.width, edited.height, edited.fps) == (info.width, info.height, info.fps)
    assert edited.audio_stream is not None and edited.duration == pytest.approx(end - start, abs=.12)
    assert updates == sorted(updates) and updates[-1] > 80
    image = video.preview_frame(payload, edited, "Trim")
    pixel = preview.getpixel((50, 45))
    assert image.getpixel((50, 45)) == pytest.approx(pixel, abs=15)


@pytest.mark.skipif(not video.video_tools_available(), reason="needs local FFmpeg and ffprobe")
def test_invalid_mp4_and_trim_bounds():
    with pytest.raises(ValueError, match="readable video"):
        video.get_video_info(b"invalid")
    payload = (SAMPLES / "sample-video.mp4").read_bytes()
    info = video.get_video_info(payload)
    with pytest.raises(ValueError, match="after"):
        video.process_video(payload, info, "Trim", start=2, end=1)
