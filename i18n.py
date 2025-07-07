# i18n.py
TRANSLATIONS = {
    "pt": {"File": "Ficheiro", "Analyze": "Analisar"},
    "en": {"File": "File", "Analyze": "Analyze"}
}
LANG = "pt" # Pode ser alterado por uma configuração
def _(text):
    return TRANSLATIONS[LANG].get(text, text)

# No ui.py
from i18n import _
self.files_tab = ttk.Frame(self.notebook)
self.notebook.add(self.files_tab, text=_("Detailed List"))
