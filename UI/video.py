"""MP4 editing with a fast still-frame preview and explicit full processing."""

import streamlit as st

from UI.image_controls import brightness_offset
from UI.media_session import (
    commit, open_file, output_name, recovery_buttons, session, source_error,
)
from Video import video_effects as video


def read_video(payload):
    """Bind the uploaded bytes to verified stream settings."""
    return payload, video.get_video_info(payload)


def video_settings(info, effect, key):
    """Map only the selected controls to video processing arguments."""
    value = None
    start, end = 0.0, info.duration
    if effect == "Posterization":
        value = st.select_slider("Colour levels", (2, 4, 8, 16, 32), value=8, key=f"{key}-levels")
    elif effect == "Brightness":
        value = brightness_offset(st.slider("Brightness", 0, 100, 50, key=f"{key}-brightness",
                                            help="50 keeps brightness unchanged."))
    elif effect == "Trim":
        start = st.number_input("Start (s)", 0.0, info.duration, 0.0, step=0.05, format="%.3f", key=f"{key}-start")
        end = st.number_input("End (s)", 0.0, info.duration, info.duration, step=0.05, format="%.3f", key=f"{key}-end")
    return value, start, end


def show_video(clip, title):
    """Display the clip with actual dimensions, duration, frame rate and sound presence."""
    payload, info = clip
    st.markdown(f"**{title}**")
    st.video(payload, format="video/mp4")
    sound = "Audio" if info.audio_stream is not None else "Silent"
    st.caption(f"{info.width} × {info.height} px · {info.duration:.2f} s · {float(info.fps):.2f} fps · {sound}")


def render_video():
    """Preview a frame and apply an effect to the whole selected MP4."""
    state = session("Video")
    if not video.video_tools_available():
        st.warning("Install FFmpeg and ffprobe on your PATH to enable Video. The other media tools are ready.")
        return
    with st.container(horizontal=True, key="media-toolbar", vertical_alignment="center"):
        open_file("Video", ["mp4"], read_video, sample="sample-video.mp4")
        actions = st.container(horizontal=True, vertical_alignment="center")
    source_error(state)
    if state["original"] is None:
        st.info("Open a short MP4 clip or try the sample video.")
        return

    payload, info = state["edited"]
    key = f"video-{state['settings']}"
    controls, workspace = st.columns([1, 3.25], gap="medium")
    with controls:
        effect = st.selectbox("Effect", (*video.EFFECTS, "Trim"), index=None,
                              placeholder="Choose an effect", key=key)
        value, start, end = video_settings(info, effect, key)
        settings = effect, value, start, end
        valid = effect is not None and start < end
        if effect and not valid:
            st.error("Choose an end time after the start.")
        if st.button("Preview frame", icon=":material/visibility:", disabled=not valid):
            state.pop("frame", None)
            try:
                with st.spinner("Reading a frame…"):
                    state["frame"] = settings, video.preview_frame(payload, info, effect, value, start=start)
            except ValueError as exc:
                st.error(str(exc))
        if effect:
            with st.expander("How It Works"):
                st.write("MediaLab reads each frame, applies the same operation as the Image tool and writes the frames to MP4. Trim keeps frames in the selected time range. The first audio track is encoded with the export when present.")
    with actions:
        apply = st.button("Apply", icon=":material/check:", type="primary", disabled=not valid)
        recovery_buttons(state, pending=effect is not None)
        st.download_button("Save MP4", payload, output_name(state, "mp4"), mime="video/mp4",
                           disabled=effect is not None, on_click="ignore", icon=":material/download:")
    with workspace:
        if apply:
            progress = st.progress(0, text="Processing video…")
            try:
                result = video.process_video(payload, info, effect, value, start=start, end=end,
                                             progress=progress.progress)
            except ValueError as exc:
                progress.empty()
                st.error(str(exc))
            else:
                commit(state, result)
                st.rerun()
        st.caption("Select Apply to process the selected clip." if effect else "Ready to edit or save.")
        before, after = st.columns(2)
        with before:
            show_video(state["original"], "Original")
        with after:
            show_video(state["edited"], "Edited")
        if "frame" in state and state["frame"][0] == settings:
            st.markdown("**Frame preview**")
            st.image(state["frame"][1], width=440, alt="Processed frame preview")
