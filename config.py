from pathlib import Path
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
MODELS_DIR = BASE_DIR
REFERENCE_IMAGE_DIR = ASSETS_DIR / "reference_images"

LOGO_PATH = ASSETS_DIR / "logo.png"
TITLE_PATH = ASSETS_DIR / "title.png"
BACKGROUND_PATH = ASSETS_DIR / "background.png"
CSS_PATH = ASSETS_DIR / "custom.css"

def get_secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default))
    except Exception:
        return default

OPENWEATHER_API_KEY = get_secret("OPENWEATHER_API_KEY")
