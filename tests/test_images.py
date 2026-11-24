"""Verify the taught formulas, supported image modes, and nonmutating filters."""

from io import BytesIO

import numpy as np
from PIL import Image
import pytest

from Images import Image_filters as filters
from Images import image_histogram as hist
from Images.image_draw import draw_shape, pencil_stroke, pick_color
from Images.image_io import download_name, png_bytes, read_image
from UI.drawing import draw_strokes, pixel_position
from UI.image_controls import brightness_offset, channel_gain, intensity_cutoff


ALL_FILTERS = [
    (filters.posterize_n_levels, (4,)),
    (filters.sepia_matrix, ()),
    (filters.negative, ()),
    (filters.grayscale_average, ()),
    (filters.make_sunset, ()),
    (filters.adjust_rgb_channels, ()),
    (filters.rotate_image_by_angle, (90,)),
    (filters.mirror_horizontal, ()),
    (filters.mirror_vertical, ()),
    (filters.adjust_brightness, (0.5,)),
    (filters.adjust_contrast, (0.5,)),
    (filters.blur_image, (2,)),
    (filters.binary_threshold, (128,)),
    (filters.blend_images, (Image.new("RGB", (3, 4), "blue"), 0.5)),
]


@pytest.mark.parametrize("mode", ["L", "RGB", "RGBA", "P"])
@pytest.mark.parametrize("operation,args", ALL_FILTERS, ids=[fn.__name__ for fn, _ in ALL_FILTERS])
def test_filters_leave_sources_unchanged(mode, operation, args):
    image = Image.new("RGBA", (5, 4), (35, 70, 90, 125)).convert(mode)
    before = image.tobytes()
    arg_bytes = [arg.tobytes() for arg in args if isinstance(arg, Image.Image)]
    result = operation(image, *args)
    assert result.mode == ("RGBA" if image.has_transparency_data else "RGB") and result is not image
    assert image.mode == mode and image.tobytes() == before
    assert [arg.tobytes() for arg in args if isinstance(arg, Image.Image)] == arg_bytes


def test_channel_formulas():
    img = Image.new("RGB", (1, 1), (90, 150, 240))
    assert filters.grayscale_average(img).getpixel((0, 0)) == (160, 160, 160)
    assert filters.negative(img).getpixel((0, 0)) == (165, 105, 15)
    assert filters.sepia_matrix(img).getpixel((0, 0)) == (196, 175, 136)
    assert filters.make_sunset(img, 0.5).getpixel((0, 0)) == (90, 75, 120)
    assert filters.adjust_rgb_channels(img, 200, 0, 200).getpixel((0, 0)) == (180, 0, 255)
    assert filters.adjust_brightness(img, 0).getpixel((0, 0)) == (0, 0, 0)
    assert filters.adjust_contrast(img, 0).getpixel((0, 0))[0] == 142
    assert filters.binary_threshold(img, 160).getpixel((0, 0)) == (255, 255, 255)
    assert filters.binary_threshold(img, 161).getpixel((0, 0)) == (0, 0, 0)


def test_posterize_values():
    im = Image.fromarray(np.array([[0, 31, 63, 127, 128, 200, 255]], dtype=np.uint8))
    actual = np.asarray(filters.posterize_n_levels(im, 2))[0, :, 0].tolist()
    assert actual == [0, 0, 0, 0, 255, 255, 255]


def test_geometry_and_blur():
    im = Image.new("RGB", (5, 3), "black")
    im.putpixel((0, 0), (255, 0, 0))
    assert filters.mirror_horizontal(im).getpixel((4, 0)) == (255, 0, 0)
    rotated = filters.rotate_image_by_angle(im, 90)
    assert rotated.size == (3, 5)
    assert rotated.getpixel((0, 4)) == (255, 0, 0)
    assert filters.blur_image(im, 0).tobytes() == im.tobytes()
    blurred = filters.blur_image(im, 1)
    assert 0 < blurred.getpixel((0, 0))[0] < 255
    assert blurred.getpixel((1, 0))[0] > 0


def test_blend_resizes_second_and_weights_it():
    first = Image.new("RGB", (4, 5), (200, 40, 0))
    second = Image.new("RGB", (7, 2), (0, 40, 200))
    assert filters.blend_images(first, second, 0).tobytes() == first.tobytes()
    blended = filters.blend_images(first, second, 0.25)
    assert blended.size == first.size
    assert blended.getpixel((0, 0)) == (150, 40, 50)
    assert filters.blend_images(first, second, 1).getpixel((0, 0)) == (0, 40, 200)


@pytest.mark.parametrize(
    "operation,args,error", [
        (filters.posterize_n_levels, (1,), ValueError),
        (filters.posterize_n_levels, (2.5,), TypeError),
        (filters.make_sunset, (float("nan"),), ValueError),
        (filters.adjust_brightness, (10**400,), ValueError),
        (filters.adjust_rgb_channels, (True,), TypeError),
        (filters.rotate_image_by_angle, (90, (1, 2)), ValueError),
        (filters.adjust_brightness, (-0.1,), ValueError),
        (filters.adjust_contrast, (4,), ValueError),
        (filters.blur_image, (-1,), ValueError),
        (filters.binary_threshold, (256,), ValueError),
        (filters.blend_images, (Image.new("RGB", (1, 1)), 2), ValueError),
        (hist.adjust_brightness, (-256,), ValueError),
        (hist.adjust_contrast, (float("inf"),), ValueError),
        (hist.binned_histogram, (True,), ValueError),
    ],
)
def test_invalid_parameters(operation, args, error):
    with pytest.raises(error):
        operation(Image.new("RGB", (2, 2)), *args)


@pytest.mark.parametrize("bins", [8, 16, 32, 64, 128, 256])
def test_histogram_bins_preserve_total(bins):
    im = Image.fromarray(np.array([[0, 31, 32, 255]], dtype=np.uint8))
    full = hist.grayscale_histogram(im)
    assert [full[i] for i in (0, 31, 32, 255)] == [1, 1, 1, 1]
    binned = hist.binned_histogram(im, bins)
    assert len(binned) == bins and sum(binned) == 4 and binned[-1] == 1
    if bins == 8:
        assert binned == [2, 1, 0, 0, 0, 0, 0, 1]


def test_histogram_adjustments_and_plot():
    im = Image.fromarray(np.array([[0, 32, 128, 255]], dtype=np.uint8))
    assert np.asarray(hist.adjust_brightness(im, 16))[0, :, 0].tolist() == [16, 48, 144, 255]
    assert np.asarray(hist.adjust_contrast(im, 1))[0, :, 0].tolist() == [0, 32, 128, 255]
    flat = hist.adjust_contrast(im, 0)
    assert set(np.asarray(flat).ravel()) == {104}
    fig = hist.plot_histogram(im, 8, "Check counts")
    assert fig.axes[0].get_title() == "Check counts"
    assert sum(patch.get_height() for patch in fig.axes[0].patches) == 4


def test_transparency_and_visible_counts():
    im = Image.new("RGBA", (2, 1), (255, 0, 0, 0))
    im.putpixel((1, 0), (40, 50, 60, 120))
    counts = hist.grayscale_histogram(im)
    assert sum(counts) == 1 and counts[48] == 1
    assert hist.adjust_brightness(im, 0).tobytes() == im.tobytes()
    assert filters.negative(im).getpixel((0, 0)) == (0, 255, 255, 0)
    assert filters.negative(im).getpixel((1, 0)) == (215, 205, 195, 120)
    assert filters.adjust_contrast(im, 0).getpixel((1, 0)) == (48, 48, 48, 120)


def test_blend_and_blur_do_not_bring_hidden_colour_into_view():
    hidden = Image.new("RGBA", (3, 1), (0, 255, 0, 0))
    opaque = Image.new("RGB", (3, 1), (240, 0, 0))
    assert filters.blend_images(hidden, opaque, 0).tobytes() == hidden.tobytes()
    assert filters.blend_images(hidden, opaque, 1).tobytes() == opaque.tobytes()
    assert filters.blend_images(hidden, opaque, 0.5).getpixel((0, 0)) == (240, 0, 0, 128)
    hidden.putpixel((1, 0), (255, 0, 0, 255))
    blurred = filters.blur_image(hidden, 1)
    red, green, blue, alpha = blurred.getpixel((0, 0))
    assert red >= 250 and green == blue == 0 and 0 < alpha < 255


def test_neutral_and_endpoint_mappings():
    assert [brightness_offset(x) for x in (0, 50, 100)] == [-128, 0, 128]
    assert [channel_gain(x) for x in (0, 50, 100)] == [0, 1, 2]
    assert [intensity_cutoff(x) for x in (0, 50, 100)] == [0, 128, 255]
    im = Image.new("RGBA", (4, 3), (31, 49, 127, 73))
    neutral = [
        hist.adjust_brightness(im, 0), filters.adjust_contrast(im, 1),
        filters.adjust_rgb_channels(im), filters.make_sunset(im, 1),
        filters.blur_image(im, 0), filters.adjust_brightness(im, 1),
        filters.rotate_image_by_angle(im, 0),
    ]
    assert all(result.tobytes() == im.tobytes() and result is not im for result in neutral)
    assert hist.adjust_brightness(im, 128).getpixel((0, 0)) == (159, 177, 255, 73)
    assert hist.adjust_brightness(im, -128).getpixel((0, 0)) == (0, 0, 0, 73)
    assert filters.adjust_rgb_channels(im, 0, 200, 200).getpixel((0, 0)) == (0, 98, 254, 73)
    assert filters.binary_threshold(im, 0).getpixel((0, 0)) == (255, 255, 255, 73)
    assert filters.binary_threshold(im, 255).getpixel((0, 0)) == (0, 0, 0, 73)


def test_rgba_geometry_and_rotation_bounds():
    im = Image.new("RGBA", (5, 3), (0, 0, 0, 0))
    im.putpixel((0, 0), (255, 0, 0, 180))
    assert filters.mirror_vertical(im).getpixel((0, 2)) == (255, 0, 0, 180)
    assert filters.rotate_image_by_angle(im, 90, max_pixels=15).size == (3, 5)
    rotated = filters.rotate_image_by_angle(im, 23)
    assert rotated.mode == "RGBA" and rotated.getpixel((0, 0))[3] == 0
    with pytest.raises(ValueError, match="too large"):
        filters.rotate_image_by_angle(im, 23, max_pixels=15)


@pytest.mark.parametrize("mode,fmt", [("L", "PNG"), ("RGB", "JPEG"), ("RGBA", "PNG"), ("P", "GIF")])
def test_read_upload_and_png_download(mode, fmt):
    image = Image.new(mode, (4, 3))
    content = BytesIO()
    image.save(content, fmt)
    restored = read_image(content.getvalue())
    assert restored.size == image.size
    assert restored.mode == ("RGBA" if mode == "RGBA" else "RGB")
    with Image.open(BytesIO(png_bytes(restored))) as png:
        assert png.format == "PNG"
        assert png.tobytes() == restored.tobytes()


def test_bad_upload_and_safe_download_name():
    for payload in (b"", b"fake PNG"):
        with pytest.raises(ValueError):
            read_image(payload)
    unsupported = BytesIO()
    Image.new("RGB", (2, 2)).save(unsupported, "PPM")
    with pytest.raises(ValueError, match="Unsupported"):
        read_image(unsupported.getvalue())
    too_wide = Image.new("L", (6001, 1))
    with pytest.raises(ValueError, match="6000"):
        read_image(png_bytes(too_wide))
    assert download_name(r"C:\outside\image #2.png", "Binary threshold") == "image-2-binary-threshold.png"


@pytest.mark.parametrize(
    "tool,point", [("Line", (10, 10)), ("Rectangle", (6, 2)), ("Ellipse", (6, 2))],
)
def test_existing_drawing_tools(tool, point):
    im = Image.new("RGB", (16, 16), "white")
    draw_shape(im, tool, (2, 2), (10, 10), "#ff0000", 2)
    assert pick_color(im, *point) == (255, 0, 0)
    assert pick_color(im, 14, 14) == (255, 255, 255)


def test_pencil_and_canvas_copy():
    im = Image.new("RGB", (20, 20), "white")
    pencil_stroke(im, (4, 4), (4, 4), "#000000", 1)
    assert pick_color(im, 4, 4) == (0, 0, 0)
    result = draw_strokes(im, [("Pencil", ((12, 2), (12, 12)), "#003399", 3, False)])
    assert pick_color(result, 12, 7) == (0, 51, 153)
    assert pick_color(im, 12, 7) == (255, 255, 255)
    assert result.size == im.size


def test_full_size_drawing_and_filled_shape():
    im = Image.new("RGBA", (1800, 1000), (0, 0, 0, 0))
    assert pixel_position((0, 0), (800, 400), im.size) == (0, 0)
    assert pixel_position((799, 399), (800, 400), im.size) == (1799, 999)
    assert pixel_position((0, 0), (1, 1), (1, 1)) == (0, 0)
    result = draw_strokes(im, [("Rectangle", ((20, 40), (200, 300)), "#003399", 4, True)])
    assert result.size == (1800, 1000)
    assert result.getpixel((100, 100)) == (0, 51, 153, 255)
    assert result.getpixel((0, 0)) == (0, 0, 0, 0)
