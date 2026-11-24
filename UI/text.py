"""Plain-text editing and safe HTML preview and export."""

import streamlit as st

from Text import text_operations as text
from UI.media_session import (
    commit, load_source, open_file, output_name, recovery_buttons, session, source_error,
)


EFFECTS = {
    "Uppercase": text.uppercase_text,
    "Lowercase": text.lowercase_text,
    "Title case": text.titlecase_text,
    "Clean spacing": text.clean_whitespace,
}


def read_text(payload):
    """Load plain text with default formatting."""
    return text.read_text(payload), {}


def paste_input(state):
    """Allow pasted text to become the original only after confirmation."""
    key = f"paste-text-{state['upload']}"
    st.text_area("Paste text", key=key, max_chars=text.MAX_BYTES, height=120)

    def use_paste():
        load_source(state, "pasted-text.txt", st.session_state[key].encode("utf-8"), read_text)
        if not state["error"]:
            state["upload"] += 1

    st.button("Open pasted text", on_click=use_paste)


def formatting(options, key):
    """Collect the allowed typesetting options for an HTML preview."""
    fonts = tuple(text.FONTS)
    alignment = ("left", "center", "right")
    spacing = ("1", "1.5", "2")
    blocks = ("p", "h2")
    font = st.selectbox("Font family", fonts, index=fonts.index(options.get("font", fonts[0])), key=f"{key}-font")
    size = st.number_input("Font size (px)", 8, 72, options.get("size", 16), key=f"{key}-size")
    styles = {label: st.checkbox(label.capitalize(), options.get(label, False), key=f"{key}-{label}")
              for label in ("bold", "italic", "underline")}
    colour = st.color_picker("Text colour", options.get("colour", "#17243a"), key=f"{key}-colour")
    background = st.color_picker("Background colour", options.get("background", "#ffffff"), key=f"{key}-background")
    align = st.selectbox("Alignment", alignment, index=alignment.index(options.get("alignment", "left")),
                         format_func=lambda value: {"left": "Left", "center": "Centre", "right": "Right"}[value],
                         key=f"{key}-alignment")
    leading = st.selectbox("Line spacing", spacing, index=spacing.index(options.get("spacing", "1.5")),
                           key=f"{key}-spacing")
    block = st.selectbox("Text block", blocks, index=blocks.index(options.get("block", "p")),
                         format_func=lambda value: "Paragraph" if value == "p" else "Heading",
                         key=f"{key}-block")
    return {"font": font, "size": size, "colour": colour, "background": background,
            "alignment": align, "spacing": leading, "block": block, **styles}


def text_preview(current, effect, key):
    """Compute a text or formatting preview from the applied document."""
    value, options = current
    if effect == "Format as HTML":
        return value, formatting(options, key)
    if effect == "Find and replace":
        old = st.text_input("Find", key=f"{key}-find")
        new = st.text_input("Replace with", key=f"{key}-replace")
        if not old:
            return None
        updated = text.find_replace(value, old, new)
    else:
        updated = EFFECTS[effect](value)
    if len(updated.encode("utf-8")) > text.MAX_BYTES:
        raise ValueError("The edited document would exceed 256 KB.")
    return (updated, options) if updated != value else None


def show_text(value, title, key):
    """Show text with whitespace preserved and report its counts."""
    st.text_area(title, value, height=236, disabled=True, key=key)
    st.caption(f"{text.count_words(value):,} words · {text.count_characters(value):,} characters")


def render_text():
    """Open or paste a document, apply editing operations and export TXT or HTML."""
    state = session("Text")
    with st.container(horizontal=True, key="media-toolbar", vertical_alignment="center"):
        open_file("Text", ["txt"], read_text, sample="sample-text.txt", paste=paste_input)
        actions = st.container(horizontal=True, vertical_alignment="center")
    source_error(state)
    if state["original"] is None:
        st.info("Open a UTF-8 text file, paste your own text, or try the sample.")
        return

    key = f"text-{state['settings']}"
    controls, workspace = st.columns([1, 3.25], gap="medium")
    preview = None
    with controls:
        effect = st.selectbox("Effect", (*EFFECTS, "Find and replace", "Format as HTML"),
                              index=None, placeholder="Choose an effect", key=key)
        if effect:
            try:
                preview = text_preview(state["edited"], effect, key)
            except ValueError as exc:
                st.error(str(exc))
            with st.expander("How It Works"):
                st.write("Find and replace matches exact text, including case. Words are separated by whitespace. HTML formatting escapes angle brackets, ampersands and other markup characters before applying the chosen style.")

    value, options = state["edited"]
    with actions:
        if st.button("Apply", icon=":material/check:", type="primary", disabled=preview is None):
            commit(state, preview)
            st.rerun()
        recovery_buttons(state, pending=effect is not None)
        st.download_button("Save TXT", value.encode("utf-8"), output_name(state, "txt"), mime="text/plain",
                           disabled=preview is not None, on_click="ignore", icon=":material/download:")
        st.download_button("Save HTML", text.generate_html_document(value, options), output_name(state, "html"),
                           mime="text/html", disabled=preview is not None, on_click="ignore",
                           icon=":material/download:")
    with workspace:
        st.caption("Preview only · Apply to keep these changes." if preview is not None else "Ready to edit or save.")
        before, after = st.columns(2)
        with before:
            show_text(state["original"][0], "Original text", f"{key}-original")
        with after:
            result, styles = preview if preview is not None else (value, options)
            html_default = effect == "Format as HTML" or bool(styles)
            view = st.segmented_control("Preview format", ("Plain text", "HTML"),
                                        default="HTML" if html_default else "Plain text", required=True,
                                        key=f"{key}-view-{html_default}", label_visibility="collapsed")
            if view == "HTML":
                st.html(text.format_html(result, styles))
                st.caption(f"{text.count_words(result):,} words · {text.count_characters(result):,} characters")
            else:
                # The value is a preview, so avoid widget state preserving stale text across reruns.
                show_text(result, "Edited text", key=None)
