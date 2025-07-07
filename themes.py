# themes.py
import json
import os
from typing import Dict

# --- Paletas de Cores ---
THEMES: Dict[str, Dict[str, str]] = {
    "dark": {
        "BACKGROUND": '#2E2E2E',
        "CONTENT_BG": '#3C3C3C',
        "TEXT": '#F5F5F5',
        "ACCENT": '#007ACC',
        "SUCCESS": '#2E7D32',
        "TREE_HEADING_BG": '#2A2A2A'
    },
    "light": {
        "BACKGROUND": '#F0F0F0',
        "CONTENT_BG": '#FFFFFF',
        "TEXT": '#000000',
        "ACCENT": '#0078D7',
        "SUCCESS": '#107C10',
        "TREE_HEADING_BG": '#E1E1E1'
    }
}

# --- Lógica para gerir o tema atual ---

CONFIG_FILE = "app_config.json"
current_theme_name = "dark" # Tema padrão

def load_theme_setting():
    """Carrega a configuração de tema do ficheiro JSON."""
    global current_theme_name
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                current_theme_name = config.get("theme", "dark")
    except (IOError, json.JSONDecodeError):
        current_theme_name = "dark"

def save_theme_setting(theme_name: str):
    """Salva a configuração de tema no ficheiro JSON."""
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except (IOError, json.JSONDecodeError):
            pass
            
    config["theme"] = theme_name
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

def get_theme_colors() -> Dict[str, str]:
    """Retorna o dicionário de cores para o tema atual."""
    return THEMES.get(current_theme_name, THEMES["dark"])

# Carrega a configuração de tema ao iniciar o módulo
load_theme_setting()
