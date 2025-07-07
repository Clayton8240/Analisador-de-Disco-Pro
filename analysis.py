# analysis.py
import os
import time
import logging
import pandas as pd
from tkinter import messagebox
from typing import List, Dict

from utils import calculate_quick_hash

def run_quick_analysis(app, path: str) -> None:
    """
    Executa uma análise rápida de uma pasta, calculando tamanhos de ficheiros e subpastas.

    Args:
        app: A instância da aplicação principal para enviar atualizações de UI.
        path: O caminho da pasta a ser analisada.
    """
    folders_data, files_data = [], []
    try:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            try:
                mtime = os.path.getmtime(item_path)
                _, ext = os.path.splitext(item)
                ext = ext.lower() if ext else '.sem_extensao'
                
                if os.path.isdir(item_path):
                    size = sum(os.path.getsize(os.path.join(dp, fn)) for dp, _, fns in os.walk(item_path, onerror=lambda e:None) for fn in fns)
                    if size > 0: folders_data.append({'name': item, 'size': size, 'mtime': mtime, 'path': item_path, 'ext': ext})
                else:
                    size = os.path.getsize(item_path)
                    if size > 0: files_data.append({'name': item, 'size': size, 'mtime': mtime, 'path': item_path, 'ext': ext})
            except (PermissionError, FileNotFoundError) as e:
                logging.warning(f"Ignorando item {item_path}: {e}")
                continue
    except PermissionError as e:
        logging.error(f"Acesso negado ao ler {path}", exc_info=True)
        app.after(0, lambda: messagebox.showerror("Erro de Acesso", f"Não foi possível ler o conteúdo de:\n{path}"))
        return

    app.df_folders = pd.DataFrame(folders_data)
    app.df_files = pd.DataFrame(files_data)
    app.after(0, app.update_quick_analysis_view)


def run_duplicate_analysis(app, path: str) -> None:
    """Procura por ficheiros duplicados usando o método de hash otimizado."""
    files_by_size = {}
    for dirpath, _, filenames in os.walk(path, onerror=lambda e: logging.warning(f"Erro ao aceder a {e.filename}: {e.strerror}")):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            try:
                size = os.path.getsize(file_path)
                if size > 1024:  # Ignora ficheiros muito pequenos
                    if size not in files_by_size: files_by_size[size] = []
                    files_by_size[size].append(file_path)
            except (PermissionError, FileNotFoundError):
                continue
    
    app.duplicate_groups = []
    potential_dups = {s: files for s, files in files_by_size.items() if len(files) > 1}
    
    for _, files in potential_dups.items():
        hashes: Dict[str, List[str]] = {}
        for file in files:
            h = calculate_quick_hash(file) # Usa a nova função de hash
            if h:
                if h not in hashes: hashes[h] = []
                hashes[h].append(file)
        for h, dup_files in hashes.items():
            if len(dup_files) > 1:
                app.duplicate_groups.append(dup_files)
    
    app.after(0, app.update_duplicates_view)

def run_old_files_analysis(app, path: str, days: int) -> None:
    """Identifica ficheiros não acedidos há mais de N dias."""
    cutoff = time.time() - (days * 86400)
    app.old_files = []
    for dirpath, _, filenames in os.walk(path, onerror=lambda e: logging.warning(f"Erro ao aceder a {e.filename}: {e.strerror}")):
        for f in filenames:
            full_path = os.path.join(dirpath, f)
            try:
                atime = os.path.getatime(full_path)
                if atime < cutoff:
                    app.old_files.append({"path": full_path, "atime": atime, "size": os.path.getsize(full_path)})
            except Exception as e:
                logging.warning(f"Não foi possível obter informações do ficheiro {full_path}: {e}")
                continue
    app.after(0, app.update_old_files_view)
