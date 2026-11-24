# MediaLab — Multimedia Processing Toolkit

MediaLab is a local Streamlit app for the **CPIT-380 Multimedia Technologies group project (Group 7)**. V1.2 provides a full image editor and preview layouts for Audio, Video and Text.

## Run locally

Use Python 3.12 or newer. From the project directory:

| Linux | Windows PowerShell |
| --- | --- |
| `python3 -m venv .venv` | `py -m venv .venv` |
| `.venv/bin/python -m pip install -r requirements.txt` | `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` |
| `./launch.sh` | `.\launch.bat` |

Open [MediaLab on localhost](http://127.0.0.1:8501). In an activated environment, you can also run `python -m streamlit run main.py`. In Code - OSS, select the Python executable inside `.venv`.

The app listens on loopback and turns off Streamlit usage statistics. Its working images stay in the local session. Save a PNG before closing or reloading the editor to keep your work.

## Edit an image

1. Select **Open image** to upload an image or use the included sample.
2. Pick an Image tool and change its settings. The right pane previews the edit. The left pane keeps the original for comparison.
3. Select **Apply** to keep the preview. The next tool starts from the applied image.
4. Use **Undo** to recover the previous applied image, **Reset adjustment** to discard a preview, or **Restore original** to return to the uploaded image. Restore itself can be undone.
5. Select **Save PNG** to download the applied image at full resolution. Apply or reset any pending preview first.

Use **How It Works** for CPIT-380 formulas and concepts. The controls provide enough guidance to work with it closed.

| Tool | What you can do |
| --- | --- |
| Filters | Grayscale, Invert Colours, Sepia, Sunset, Posterization and Black and White. |
| Adjustments | Brightness, Contrast, Colour balance and Blur. |
| Transformations | Rotate clockwise, flip horizontally or flip vertically. |
| Combination | Blend with a second image. Try `samples/blue-study.png`. |
| Drawing | Pencil, line, outlined or filled rectangle and ellipse, colour picker and eyedropper. Undo individual strokes or clear the draft before applying it. |
| Histogram | Compare the original and current result on shared axes. Adjust brightness and contrast and choose 8, 16, 32, 64, 128 or 256 bins. |

## Parameter mappings

| Control | Default | Processing value |
| --- | --- | --- |
| Brightness 0–100 | 50 | Add `round((value − 50) × 128 / 50)` to each colour channel. |
| Contrast 0–100 | 50 | Multiply distance from the mean visible intensity by `value / 50`. |
| Red, Green and Blue 0–100 | 50 each | Multiply each channel by `value / 50`, independently. |
| Blur strength 0–100 | 0 | Gaussian radius in pixels equals `value / 5`. |
| Filter intensity 0–100% | 100% | Mix the edited image with its filtered version, using `value / 100` for the effect. |
| Blend amount 0–100% | 50% | Use `value / 100` as the weight for the second image. |
| Sunset intensity 0–100% | 0% | Scale green and blue by `1 − value / 100` and keep red fixed. |
| Black and White cutoff 0–100% | 50% | Set the inclusive white cutoff to `round(255 × value / 100)`. |
| Rotation, brush thickness, posterization and bin counts | Tool-specific | Degrees, pixels, discrete colour levels and bin counts respectively. |

Colour results are rounded and clipped to the 8-bit range. Grayscale retains the course's whole-number average. The histogram uses Pillow luminance levels, with fully transparent pixels excluded and partially transparent pixels counted once. Colour effects preserve alpha. Rotation, blur and blending use opacity when combining colours to avoid hidden-colour halos.

## Project layout and checks

- `main.py` routes Image, Audio, Video and Text.
- `Images/` contains Pillow and NumPy processing, drawing, histogram calculations and image input/output.
- `UI/` handles the workflow, friendly controls, previews and disabled future sections.
- `Sound/`, `Video/` and `Text/` contain the planned operation signatures as TODO comments.
- `tests/` covers formulas and the editor workflow. `samples/` contains two generated illustrations.

Install `requirements-dev.txt` in the environment, then verify:

~~~sh
python -m pytest -q
python -m compileall -q main.py Images UI Sound Video Text tests
~~~

The standalone drawing window is available through `python -m Images.image_draw` when Tkinter is installed.

## Current limits

- Image input supports PNG, JPEG, BMP, WebP, GIF and TIFF, up to 20 MB, 12 megapixels and 6000 pixels per side. Multi-frame files open at the first frame. PNG is the export format.
- Rotation expands the canvas and rejects angles that would exceed the 24-megapixel working limit. It fills new corners white on opaque images and leaves them transparent on images with alpha.
- Blending resizes the second image to match the current edit. Drawing keeps the edited image's full resolution and uses a pointer on a scaled preview.
- Editing history keeps up to five applied versions and reduces that count for large images. Opening another image starts a new session for that image.
- Audio, Video and Text expose disabled layouts while their processors are being developed. See the [roadmap](ROADMAP.md).
