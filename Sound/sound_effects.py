"""Planned PCM editing operations. The Audio workbench is a preview layout."""

# TODO adjust_volume(sound, factor): Multiply sample amplitudes and clamp to the sample range.
# TODO reverse_sound(sound): Reverse frame order while keeping each frame's channels together.
# TODO add_echo(sound, delay, strength): Add a delayed, quieter copy to the source.
# TODO trim_sound(sound, start, end): Convert time bounds to sample positions and extract the range.
# TODO splice_sounds(sound1, sound2): Join clips with compatible sample rate and channels.
# TODO blend_sounds(sound1, sound2, weight): Combine corresponding samples with normalized weights.
# Optional TODO fade_in(sound, duration): Ramp up from silence across the first frames.
# Optional TODO fade_out(sound, duration): Ramp down to silence across the last frames.
# Optional TODO get_waveform(sound): Return an amplitude view for the waveform plot.
