import base64
from pathlib import Path
import streamlit as st

def _data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    suffix = path.suffix.lower().lstrip(".")
    mime = "jpeg" if suffix in {"jpg", "jpeg"} else suffix
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:image/{mime};base64,{encoded}"

def apply_theme(css_path: Path, background_path: Path) -> None:
    css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""
    css = css.replace("__BACKGROUND_DATA_URI__", _data_uri(background_path))
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
