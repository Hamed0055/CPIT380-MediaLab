# MediaLab sample pack

Ready-to-use CPIT-380 demonstration and testing assets. Copy the four folders into your project’s `samples/` directory. No external downloads or extra dependencies are needed to use the files.

## Fast demonstration (recommended)

1. Image: open `images/09_nasa_astronaut.jpg` or `03_landscape_day.jpg`; invert, adjust RGB, and compare histograms.
2. Histogram: open `01_grayscale_ramp.png`. The histogram has exactly 720 pixels per intensity, or 184,320 pixels in total; with 32 bins expect 5,760 per bin.
3. Blend: use day and night landscape files together. Both are 800 × 500.
4. Audio: use `audio/01_spoken_demo.wav` for reverse and echo, and `04_blend_A.wav` / `05_blend_B.wav` for blend or splice.
5. Video: use `video/01_moving_shapes.mp4` to show frame-based effects. Use `03_stereo_sync.mp4` to verify original audio is retained.
6. Text: use `text/01_messy_notes.txt` for cleanup, then `02_short_article.txt` for formatting.

## File catalog

### Images

| File | Suggested use |
|---|---|
| `01_grayscale_ramp.png` | Histogram binning, grayscale, threshold, posterization. Each of 256 levels occurs exactly 720 times. |
| `02_rgb_color_chart.png` | RGB sliders, inversion, grayscale, eyedropper, sepia. |
| `03_landscape_day.jpg` | Casual demonstration: filters, brightness, contrast, blur, rotation and drawing. |
| `04_landscape_night.png` | Blend with 03_landscape_day.jpg; same dimensions (800×500). |
| `05_low_contrast.png` | Contrast, histogram stretching and equalization; intentionally narrow intensity distribution. |
| `06_dark_image.png` | Brightness recovery and histogram shift. |
| `07_asymmetric_shapes.png` | Mirroring, arbitrary rotation, pencil, lines, shapes and coordinate mapping. |
| `08_transparent.png` | Transparency handling, import/export and drawing on alpha images. |
| `09_nasa_astronaut.jpg` | Real-world photographic filter demonstration, RGB, blur, sepia and histogram. |
| `10_nasa_hubble.jpg` | Real-world dark photograph, brightness and contrast; rich fine details. |
| `11_blank_canvas.png` | Drawing tools and shape placement on a white background. |

### Audio

| File | Suggested use |
|---|---|
| `01_spoken_demo.wav` | Speech makes reverse, echo and volume changes immediately recognizable. |
| `02_tone_440hz.wav` | Volume, waveform, fades and frequency reference (440 Hz). |
| `03_echo_clicks.wav` | Echo and silence; short isolated tones expose delays clearly. |
| `04_blend_A.wav` | First input for blend/splice; mono, 4 seconds, matching B. |
| `05_blend_B.wav` | Second input for blend/splice; mono, 4 seconds, matching A. |
| `06_stereo_channels.wav` | Stereo integrity: left tone first, right tone second; test frame-aware reverse. |
| `07_quiet_tone.wav` | Volume boost and normalization tests. |

### Video

| File | Suggested use |
|---|---|
| `01_moving_shapes.mp4` | Frame processing, inversion, mirroring, grayscale and timing; silent. |
| `02_landscape_pan.mp4` | Natural-looking illustrated motion; posterization, blur, brightness and contrast; silent. |
| `03_stereo_sync.mp4` | Check original audio preservation and audio/video sync after effects. |

### Text

| File | Suggested use |
|---|---|
| `01_messy_notes.txt` | Whitespace cleanup, case conversion, find and replace. |
| `02_short_article.txt` | Text formatting, headings, paragraphs and HTML export. |
| `03_unicode.txt` | UTF-8, Unicode, Arabic and accented letters. |
| `04_html_escape_test.txt` | Safe HTML generation; angle brackets must display as text. |
| `05_repeated_lines.txt` | Sorting, duplicate removal and line operations (optional). |

## Rights and attribution

Except for the two NASA images, assets were generated for this pack using original procedural designs, synthesized tones, original written text and generic eSpeak speech. You may use, modify and redistribute these generated samples with your coursework/repository to the extent rights apply; no third-party music or stock footage is embedded. No guarantee is made about copyright status in every jurisdiction.

NASA images: the scikit-image documentation identifies both sample photographs as public-domain material. See `SOURCES.md` for individual attribution and NASA usage guidance. Do not imply NASA endorsement.

## Technical notes

- Images: PNG and JPEG, including grayscale and RGBA.
- Audio: uncompressed PCM WAV, signed 16-bit, mono and stereo.
- Video: 640 × 360, 24 fps, H.264 MP4 (browser-friendly); two silent clips and one with stereo AAC audio.
- Text: UTF-8 plain text.
- `manifest.json` records dimensions, formats, durations and SHA-256 checksums.
- These assets were validated for decoding/readability, not run through MediaLab itself.
