"""Preview the future editing layouts with disabled controls."""

import streamlit as st


SECTIONS = {
    "Audio": {
        "formats": ["wav"], "save": "Save WAV",
        "effects": ("Volume", "Reverse", "Echo", "Trim", "Join clips", "Blend"),
        "views": ("Original playback", "Edited playback"),
        "information": "Duration · Sample rate · Channels",
    },
    "Video": {
        "formats": ["mp4"], "save": "Save MP4",
        "effects": ("Grayscale", "Invert Colours", "Posterization", "Brightness", "Trim"),
        "views": ("Original video", "Edited video"),
        "information": "Resolution · Duration · Frame rate",
    },
    "Text": {
        "formats": ["txt"], "save": "Save TXT / HTML",
        "effects": ("Uppercase", "Lowercase", "Title case", "Clean spacing", "Find and replace", "Format as HTML"),
        "views": ("Original text", "Edited text"),
        "information": "Words · Characters",
    },
}


# Planned settings: Show representative controls without offering a processing action.
def planned_settings(media, section):
    st.selectbox("Effect", section["effects"], disabled=True, key=f"planned-effect-{media}")
    if media == "Audio":
        st.slider("Volume", 0, 100, 50, disabled=True)
        with st.expander("Echo, trim and blend settings"):
            st.slider("Echo strength (%)", 0, 100, 30, disabled=True)
            st.number_input("Echo delay (ms)", 0, 2000, 250, disabled=True)
            st.number_input("Trim start (s)", min_value=0.0, value=0.0, disabled=True)
            st.number_input("Trim end (s)", min_value=0.0, value=0.0, disabled=True)
            st.slider("Blend amount (%)", 0, 100, 50, disabled=True)
    elif media == "Video":
        st.select_slider("Colour levels", (2, 4, 8, 16), value=8, disabled=True)
        st.caption("Processing progress will appear here.")
    else:
        with st.expander("Formatting"):
            st.selectbox("Font family", ("Sans serif", "Serif", "Monospace"), disabled=True)
            st.number_input("Font size", 8, 72, 16, disabled=True)
            st.segmented_control("Style", ("Bold", "Italic", "Underline"), selection_mode="multi", disabled=True)
            st.color_picker("Text colour", "#17243a", disabled=True)
            st.color_picker("Background colour", "#ffffff", disabled=True)
            st.selectbox("Alignment", ("Left", "Centre", "Right"), disabled=True)
            st.selectbox("Line spacing", ("Single", "1.5 lines", "Double"), disabled=True)
            st.selectbox("Text block", ("Paragraph", "Heading"), disabled=True)


# Render planned section: Use the image editor's toolbar and two-pane layout as a guide.
def render_planned(media):
    section = SECTIONS[media]
    with st.container(horizontal=True, key="media-toolbar", vertical_alignment="center"):
        st.button(f"Open {media.lower()}", icon=":material/folder_open:", disabled=True)
        st.button("Apply", icon=":material/check:", disabled=True)
        st.button("Reset", icon=":material/restart_alt:", disabled=True)
        st.button(section["save"], icon=":material/download:", disabled=True)
    st.info(f"{media} · Under Development")
    controls, workspace = st.columns([1, 3.25], gap="medium")
    with controls:
        st.file_uploader(f"Upload {media.lower()}", type=section["formats"], disabled=True)
        planned_settings(media, section)
    with workspace:
        st.caption(section["information"])
        for position, column in enumerate(st.columns(2)):
            with column:
                title = section["views"][position]
                st.markdown(f"**{title}**")
                if media == "Text":
                    label = "Paste text" if position == 0 else "Result preview"
                    if position == 1:
                        st.segmented_control("Preview format", ("Plain text", "HTML"),
                                             default="Plain text", disabled=True)
                    st.text_area(label, height=160, disabled=True)
                else:
                    with st.container(height=180, border=True, vertical_alignment="center"):
                        caption = f"Open a {section['formats'][0].upper()} file to preview." if position == 0 else "The result will appear here."
                        st.caption(caption)
