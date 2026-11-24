"""WAV editing with side-by-side playback and an explicit Apply action."""

import streamlit as st

from Sound import sound_effects as sound
from UI.media_session import (
    commit, open_file, output_name, recovery_buttons, session, source_error,
)


def audio_preview(clip, effect, key):
    """Read settings and calculate one preview from the applied audio."""
    if effect == "Volume":
        volume = st.slider("Volume", 0, 100, 50, key=f"{key}-volume",
                           help="50 keeps the original level. Move right to make the clip louder.")
        return sound.adjust_volume(clip, volume / 50) if volume != 50 else None
    if effect == "Reverse":
        return sound.reverse_sound(clip)
    if effect == "Echo":
        delay = st.slider("Echo delay (ms)", 0, 2000, 250, key=f"{key}-delay")
        strength = st.slider("Echo strength (%)", 0, 100, 30, key=f"{key}-strength")
        return sound.add_echo(clip, delay / 1000, strength / 100) if strength else None
    if effect == "Trim":
        start = st.number_input("Start (s)", 0.0, clip.duration, 0.0, step=0.01, format="%.3f", key=f"{key}-start")
        end = st.number_input("End (s)", 0.0, clip.duration, clip.duration, step=0.01, format="%.3f", key=f"{key}-end")
        return sound.trim_sound(clip, start, end) if start != 0 or end != clip.duration else None
    uploaded = st.file_uploader("Open second WAV", type=["wav"], key=f"{key}-second")
    if uploaded is None:
        return None
    other = sound.read_wav(uploaded.getvalue())
    if effect == "Join clips":
        return sound.splice_sounds(clip, other)
    blend = st.slider("Second clip (%)", 0, 100, 50, key=f"{key}-blend")
    return sound.blend_sounds(clip, other, blend / 100) if blend else None


def show_audio(clip, title):
    """Display a playable WAV and the properties users can compare."""
    st.markdown(f"**{title}**")
    st.audio(sound.wav_bytes(clip), format="audio/wav")
    channel_label = "Mono" if clip.channels == 1 else "Stereo"
    st.caption(f"{clip.duration:.2f} s · {clip.rate:,} Hz · {channel_label} · {clip.width * 8}-bit PCM")


def render_audio():
    """Open a WAV, preview an effect and save the applied result."""
    state = session("Audio")
    with st.container(horizontal=True, key="media-toolbar", vertical_alignment="center"):
        open_file("Audio", ["wav"], sound.read_wav, sample="sample-tone.wav")
        actions = st.container(horizontal=True, vertical_alignment="center")
    source_error(state)
    if state["original"] is None:
        st.info("Open a mono or stereo PCM WAV file, or try the sample audio.")
        return

    key = f"audio-{state['settings']}"
    controls, workspace = st.columns([1, 3.25], gap="medium")
    preview = None
    with controls:
        effect = st.selectbox("Effect", ("Volume", "Reverse", "Echo", "Trim", "Join clips", "Blend"),
                              index=None, placeholder="Choose an effect", key=key)
        if effect:
            try:
                preview = audio_preview(state["edited"], effect, key)
            except ValueError as exc:
                st.error(str(exc))
            with st.expander("How It Works"):
                st.write({
                    "Volume": "Volume multiplies each sample and clips values outside the PCM range.",
                    "Reverse": "Reverse reads sample frames in the opposite order. Stereo left and right stay together.",
                    "Echo": "Echo adds a delayed, quieter copy and extends the clip to include its tail.",
                    "Trim": "Trim uses the sample rate to convert seconds to frame positions.",
                    "Join clips": "Join appends a compatible WAV with the same rate, channels and bit depth.",
                    "Blend": "Blend adds corresponding samples using the selected weights. A shorter clip is padded with silence.",
                }[effect])
    with actions:
        if st.button("Apply", icon=":material/check:", type="primary", disabled=preview is None):
            commit(state, preview)
            st.rerun()
        recovery_buttons(state, pending=effect is not None)
        st.download_button("Save WAV", sound.wav_bytes(state["edited"]), output_name(state, "wav"),
                           mime="audio/wav", disabled=preview is not None, on_click="ignore",
                           icon=":material/download:")
    with workspace:
        st.caption("Preview only · Apply to keep these changes." if preview is not None else "Ready to edit or save.")
        original, result = st.columns(2)
        with original:
            show_audio(state["original"], "Original")
        with result:
            show_audio(preview if preview is not None else state["edited"], "Preview" if preview is not None else "Edited")
