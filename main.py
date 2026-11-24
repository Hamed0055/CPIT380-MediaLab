"""Launch the local CPIT-380 MediaLab interface."""

from pathlib import Path

import streamlit as st

from UI.images import render_image_workbench
from UI.audio import render_audio
from UI.text import render_text
from UI.video import render_video

STYLE = Path(__file__).resolve().parent / "UI" / "studio.css"


# Main: Present the common editing navigation and open the chosen media section.
def main():
    st.set_page_config(page_title="MediaLab — Multimedia Processing Toolkit", layout="wide")
    st.html(STYLE)
    with st.container(key="medialab-header", horizontal=True, horizontal_alignment="distribute",
                      vertical_alignment="center"):
        st.title("MediaLab", anchor=False)
        media = st.segmented_control(
            "Media type", ["Image", "Audio", "Video", "Text"],
            default="Image", key="media", label_visibility="collapsed", required=True,
        )
    {
        "Image": render_image_workbench,
        "Audio": render_audio,
        "Video": render_video,
        "Text": render_text,
    }[media]()


if __name__ == "__main__":
    main()
