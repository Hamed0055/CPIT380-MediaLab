"""Shared source, applied-result and undo controls for the media workbenches."""

from pathlib import Path

import streamlit as st


SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def session(kind):
    """Keep the workbench data when switching sections."""
    return st.session_state.setdefault(f"media-{kind}", {
        "original": None, "edited": None, "name": "", "error": "", "history": [],
        "settings": 0, "upload": 0,
    })


def set_source(state, name, value):
    """Start a new editing session after a valid open."""
    state.update(original=value, edited=value, name=name, error="", history=[])
    reset_settings(state)


def load_source(state, name, data, reader):
    """Keep existing edits if a new file cannot be opened."""
    try:
        set_source(state, name, reader(data))
    except ValueError as exc:
        state["error"] = str(exc)


def open_file(kind, formats, reader, *, sample=None, paste=None):
    """Present the shared Open menu and validate uploads before replacement."""
    state = session(kind)
    with st.popover(f"Open {kind.lower()}", icon=":material/folder_open:"):
        upload_key = f"upload-{kind}-{state['upload']}"

        def uploaded():
            file = st.session_state.get(upload_key)
            state["error"] = ""
            if file is not None:
                load_source(state, file.name, file.getvalue(), reader)

        st.file_uploader(f"Upload {kind.lower()}", type=formats, key=upload_key, on_change=uploaded)
        if sample:
            def use_sample():
                load_source(state, sample, (SAMPLES / sample).read_bytes(), reader)
                state["upload"] += 1

            st.button(f"Use sample {kind.lower()}", on_click=use_sample)
        if paste:
            paste(state)
        st.caption("Opening another file starts a new edit.")
    if state["name"]:
        st.text(state["name"])


def reset_settings(state):
    """Discard the preview while keeping the applied edit."""
    state["settings"] += 1
    state.pop("frame", None)


def commit(state, value):
    """Apply an edit and retain up to three previous versions."""
    state["history"].append(state["edited"])
    state["history"] = state["history"][-3:]
    state["edited"] = value
    reset_settings(state)


def undo(state):
    """Recover the previously applied version."""
    state["edited"] = state["history"].pop()
    reset_settings(state)


def recovery_buttons(state, *, pending):
    """Provide undo, reset and original recovery in the familiar toolbar."""
    st.button("Undo", icon=":material/undo:", disabled=not state["history"],
              on_click=undo, args=(state,))
    st.button("Reset adjustment", icon=":material/restart_alt:", disabled=not pending,
              on_click=reset_settings, args=(state,))
    st.button("Restore original", disabled=state["edited"] is state["original"],
              on_click=commit, args=(state, state["original"]))


def output_name(state, extension):
    """Derive the result name from the currently opened filename."""
    return f"{Path(state['name']).stem or 'medialab'}-edited.{extension}"


def source_error(state):
    """Report an invalid upload and whether the previous source is still open."""
    if state["error"]:
        suffix = " Your current file is still open." if state["original"] is not None else ""
        st.error(state["error"] + suffix)
