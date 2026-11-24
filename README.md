# MediaLab — Multimedia Processing Toolkit

MediaLab is a local Streamlit app for the **CPIT-380 Multimedia Technologies group project (Group 7)**. It includes four workbenches for images, audio, video and text.

## Run locally

Use Python 3.12 or newer. From the project directory:

| Linux | Windows PowerShell |
| --- | --- |
| `python3 -m venv .venv` | `py -m venv .venv` |
| `.venv/bin/python -m pip install -r requirements.txt` | `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` |
| `./launch.sh` | `.\launch.bat` |

Open [MediaLab on localhost](http://127.0.0.1:8501). In an activated environment, you can also run `python -m streamlit run main.py`. In Code - OSS, select the Python executable inside `.venv`.

For Video, install FFmpeg with the `libx264` and AAC encoders. Check that `ffmpeg -version` and `ffprobe -version` work in your terminal. Image, Audio and Text use the Python dependencies above.

The app listens on loopback and turns off Streamlit usage statistics. Each section keeps its own work during the browser session. Download the applied result before closing or reloading the page.

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

## Edit audio, video or text

| Workbench | Open | Edit and compare | Export |
| --- | --- | --- | --- |
| Audio | PCM WAV or `samples/sample-tone.wav` | Adjust volume, reverse, add echo, trim, join, or blend. Play the original and the preview before applying. | WAV at the original rate, bit depth and channel count |
| Video | MP4 or `samples/sample-video.mp4` | Grayscale, invert colours, posterize, adjust brightness, or trim. Use **Preview frame** before processing the clip. | H.264 MP4 with its first audio track encoded as AAC, when present |
| Text | UTF-8 TXT, pasted text, or `samples/sample-text.txt` | Change case, clean spacing, find and replace, or format as HTML. Compare the word and character counts. | UTF-8 TXT or a self-contained HTML document |

1. Choose a workbench at the top and use **Open** to select a file or load the included sample.
2. Choose an effect and review its settings. Audio and Text preview the result as you edit. Video processes the whole clip after you select **Apply**.
3. Select **Apply**, then select a **Save** button. Use **Undo** to recover up to three previous applied versions in Audio, Video and Text.
4. Use **Reset adjustment** to clear the current settings or **Restore original** to recover the opened file.

For Audio, a volume setting of 50 preserves the source level. Echo adds a quieter copy after the selected delay. Join and blend require matching rates, channel counts and bit depths. Blend pads the shorter clip with silence.

For Text, find and replace matches exact, case-sensitive text. HTML formatting controls the font, size, emphasis, colours, alignment and spacing. Markup characters from the source remain literal text in the exported document.

## Image parameter mappings

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
- `Sound/` implements integer PCM audio operations and WAV I/O.
- `Video/` probes and processes MP4 clips frame by frame using FFmpeg and the Image filters.
- `Text/` handles UTF-8 editing, counts and HTML output.
- `UI/` handles the editing workflow, controls and previews.
- `tests/` covers media processing and the editing workflow. `samples/` contains generated demonstration files.

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
- Audio accepts mono or stereo integer PCM WAV, at 8, 16, 24 or 32 bits and 1–96 kHz. Inputs are limited to 20 MB and 60 seconds. Join and echo exports use the same limits.
- Video accepts MP4 inputs up to 20 MB and 30 seconds, with a maximum of 1080p and 60 fps. Source playback depends on the codecs supported by your browser. Exports use a constant frame rate. Extra audio tracks and subtitles are omitted.
- Text accepts UTF-8 documents up to 256 KB. Words are counted as whitespace-separated sequences. The character count includes spaces and line breaks.

See the [roadmap](ROADMAP.md) for optional improvements.
