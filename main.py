"""Launch the local CPIT-380 MediaLab interface."""

import streamlit as st

from UI.images import render_image_workbench


PLANNED = {
    "Sound": (
        "Volume adjustment, reverse, echo, splicing and blending.",
        "Choose an audio file",
        ["wav", "mp3", "flac", "ogg"],
    ),
    "Video": (
        "Frame-based grayscale, negative, posterization and other image effects.",
        "Choose a video file",
        ["mp4", "mov", "avi", "webm"],
    ),
    "Text": (
        "Text formatting, case conversion, find and replace, whitespace cleanup and HTML generation.",
        "Enter text",
        None,
    ),
}


# Render placeholder: Show the planned controls without accepting or processing inputs.
def render_placeholder(media):
    features, label, types = PLANNED[media]
    st.header(media)
    st.info(f"{media} processing is under development.")
    with st.container(border=True):
        if types is None:
            st.text_area(label, disabled=True)
        else:
            st.file_uploader(label, type=types, disabled=True)
        st.button("Process", key=f"process-{media}", disabled=True)
    st.markdown(f"**Planned operations**  \n{features}")


# Main: Route the four sections through a single set of navigation controls.
def main():
    st.set_page_config(
        page_title="MediaLab — Multimedia Processing Toolkit",
        page_icon="🖼️",
        layout="wide",
    )
    st.title("MediaLab — Multimedia Processing Toolkit")
    media = st.segmented_control(
        "Media type", ["Image", "Sound", "Video", "Text"],
        default="Image", key="media", label_visibility="collapsed",
        required=True,
    )
    if media == "Image":
        render_image_workbench()
    else:
        render_placeholder(media)


if __name__ == "__main__":
    main()
