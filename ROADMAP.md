# MediaLab roadmap

V1.2 completes the Image workbench. The next phases use the same workflow: open, edit, preview, apply and save. Add each processor as a plain Python function with tests before wiring it into Streamlit.

| Priority | Essential proposal work | Later improvements |
| --- | --- | --- |
| 1. Audio | Read and export PCM WAV. Implement volume, reverse and echo with frame-aware operations. Preserve rate, channels and sample width and test clipping boundaries. | Trim, join, blend, fades, waveform display and MP3 if straightforward. |
| 2. Video | Read a short MP4, report dimensions, frame rate and duration, then apply grayscale, inversion and posterization one frame at a time using the Image modules. Display progress and clean up temporary files. | Frame extraction, trimming, brightness, contrast, flipping and retaining source audio where practical. |
| 3. Text | Read or paste plain text. Add case changes, whitespace cleanup, literal find and replace, counts and escaped HTML output. Provide TXT and HTML export. | Additional formatting, line order and deduplication. Keep the interface focused on plain text. |
| 4. Integration | Test all four workbenches on Linux and Windows. Prepare a repeatable demonstration and document input limits and any silent video output. | Additional codecs and detailed previews only after the required flows work. |

Planned function signatures and method notes live beside the corresponding modules in `Sound/sound_effects.py`, `Video/video_effects.py` and `Text/text_operations.py`.
