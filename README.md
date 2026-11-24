# MediaLab — Multimedia Processing Toolkit

MediaLab is a local Streamlit application for the **CPIT-380 Multimedia Technologies group project (Group 7)**. It demonstrates course image operations with an original, a processed preview, and a downloadable result.

## Run locally

Use Python 3.12 or newer. From the project directory:

| Linux | Windows PowerShell |
| --- | --- |
| `python3 -m venv .venv` | `py -m venv .venv` |
| `.venv/bin/python -m pip install -r requirements.txt` | `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` |
| `./launch.sh` | `.\launch.bat` |

Open [MediaLab on localhost](http://127.0.0.1:8501). With the environment activated, the equivalent command is `python -m streamlit run main.py`. In Code - OSS, open this folder and use **Python: Select Interpreter** to select the Python executable inside `.venv`.

Media processing happens on your machine. The app binds to loopback and turns off Streamlit usage statistics. Working images are held in the browser session and app memory.

## Phase 1

| Section | Current status |
| --- | --- |
| Image / Filters | Preview originals beside grayscale, negative, posterization, sepia, sunset, RGB changes, threshold, mirror, rotation, blur, and two-image blending. Reset and export PNG. |
| Image / Histogram & adjustments | Apply a brightness offset followed by a contrast multiplier about the mean intensity. Compare original and processed histograms on the same scale. Choose 8, 16, 32, 64, 128, or 256 bins. |
| Image / Drawing | Pencil, line, rectangle, ellipse and eyedropper, with colour and thickness controls. Reset to the original, choose a blank canvas, or save PNG. |
| Sound | Placeholder for volume, reverse, echo, splicing and blending. |
| Video | Placeholder for grayscale, negative, posterization and other frame effects. |
| Text | Placeholder for formatting, case conversion, find and replace, whitespace cleanup and HTML. |

Start with the sample image. Try **Negative**, then test **Combine → Blend two images** with `samples/blue-study.png` as the second input. Reset restores the current panel's defaults and keeps the selected original. Switching between sections retains the original during the session.

## Structure

- `main.py` routes the four sections.
- `Images/Image_filters.py` contains the original Pillow and NumPy effects and the shared contrast calculation.
- `Images/image_histogram.py` contains the additive brightness adjustment, binning, and Matplotlib chart generation. It uses the shared contrast calculation.
- `Images/image_draw.py` contains the Pillow drawing routines and the original optional Tkinter window.
- `Images/image_io.py` checks uploaded formats and encodes downloads.
- `UI/` has Streamlit controls and a small canvas that passes pointer positions to Pillow.
- `Sound/`, `Video/`, and `Text/` reserve locations for later processors.
- `tests/` contains automated formula and Streamlit tests. `samples/` holds two generated illustrations.

The histogram page uses additive brightness. The existing filter API also retains its separate multiplicative brightness function for programmatic use. Both contrast entry points use the classroom histogram's mean-based formula, including its rounding.

## Verify

Install `requirements-dev.txt` in the same environment, then run:

~~~sh
python -m pytest -q
python -m compileall -q main.py Images UI tests
~~~

The standalone drawing window is available through `python -m Images.image_draw` if Tkinter is installed.

## Limits

- Uploads support PNG, JPEG, BMP, WebP, GIF, and TIFF up to 20 MB, 12 megapixels, and 6000 pixels per side. Multi-frame input uses the first frame. Exports are PNG.
- The existing effects and drawing workflow composite transparency onto white. The original upload is kept in memory, and the unfiltered preview and PNG preserve its alpha. Blending resizes the second input to the original dimensions.
- Drawing exports fit the source onto an 800 × 500 canvas. A pointer is needed to draw.
- Phase 1 implements image processing. The three remaining sections display disabled input and processing controls.

## Next development step

Implement and test one standalone Sound processor first. Use the same input, settings, preview, and export flow when connecting it to the interface.
