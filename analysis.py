# analysis.py
import os
import time
import logging
import pandas as pd
from tkinter import messagebox
from typing import List, Dict, TYPE_CHECKING

# Importa o módulo de internacionalização
import i18n

if TYPE_CHECKING:
    from ui import FinalDiskAnalyzerApp

from utils import calculate_quick_hash, categorize_file
_ = i18n.get_text

def run_quick_analysis(app: 'FinalDiskAnalyzerApp', path: str) -> None:
    """
    Executa uma análise rápida de um diretório, listando ficheiros e pastas.
    """
    folders_data, files_data = [], []
    try:
        # Pre-contagem para a barra de progresso
        list_of_items = os.listdir(path)
        app.after(0, app.set_determinate_progress, len(list_of_items))
        
        for i, item in enumerate(list_of_items):
            item_path = os.path.join(path, item)
            try:
                mtime = os.path.getmtime(item_path)
                _, ext = os.path.splitext(item)
                ext = ext.lower() if ext else '.sem_extensao'
                
                if os.path.isdir(item_path):
                    size = sum(os.path.getsize(os.path.join(dp, fn)) for dp, _, fns in os.walk(item_path, onerror=lambda e:None) for fn in fns)
                    if size > 0:
                        folders_data.append({'name': item, 'size': size, 'mtime': mtime, 'path': item_path, 'ext': ext})
                else:
                    size = os.path.getsize(item_path)
                    if size > 0:
                        files_data.append({'name': item, 'size': size, 'mtime': mtime, 'path': item_path, 'ext': ext})
            except (PermissionError, FileNotFoundError) as e:
                logging.warning(f"Ignorando item inacessível {item_path}: {e}")
                continue
            finally:
                app.after(0, app.update_progress_value, i + 1)

    except PermissionError as e:
        logging.error(f"Acesso negado ao ler o diretório {path}", exc_info=True)
        app.after(0, lambda: messagebox.showerror(_("error_open_folder"), f"{_('error_open_folder')}\n{path}"))
        return

    app.df_folders = pd.DataFrame(folders_data)
    app.df_files = pd.DataFrame(files_data)
    app.after(0, app.update_quick_analysis_view)


def run_duplicate_analysis(app: 'FinalDiskAnalyzerApp', path: str) -> None:
    """
    Procura por ficheiros duplicados num diretório usando uma abordagem otimizada.
    """
    files_by_size: Dict[int, List[str]] = {}
    all_files = [os.path.join(dp, f) for dp, dn, fn in os.walk(path, onerror=lambda e: logging.warning(f"Erro ao aceder a {e.filename}: {e.strerror}")) for f in fn]
    
    app.after(0, app.set_determinate_progress, len(all_files))

    for i, file_path in enumerate(all_files):
        try:
            size = os.path.getsize(file_path)
            if size > 1024:
                if size not in files_by_size:
                    files_by_size[size] = []
                files_by_size[size].append(file_path)
        except (PermissionError, FileNotFoundError):
            continue
        finally:
            if i % 100 == 0:
                app.after(0, app.update_progress_value, i)
    
    app.duplicate_groups = []
    potential_dups = {s: files for s, files in files_by_size.items() if len(files) > 1}
    
    for _, files in potential_dups.items():
        hashes: Dict[str, List[str]] = {}
        for file in files:
            h = calculate_quick_hash(file)
            if h:
                if h not in hashes:
                    hashes[h] = []
                hashes[h].append(file)
        
        for h, dup_files in hashes.items():
            if len(dup_files) > 1:
                app.duplicate_groups.append(dup_files)
    
    app.after(0, app.update_duplicates_view)

def run_old_files_analysis(app: 'FinalDiskAnalyzerApp', path: str, days: int) -> None:
    """
    Identifica ficheiros que não foram acedidos há mais de N dias.
    """
    cutoff = time.time() - (days * 86400)
    app.old_files = []
    all_files = [os.path.join(dp, f) for dp, dn, fn in os.walk(path, onerror=lambda e: logging.warning(f"Erro ao aceder a {e.filename}: {e.strerror}")) for f in fn]

    app.after(0, app.set_determinate_progress, len(all_files))

    for i, full_path in enumerate(all_files):
        try:
            atime = os.path.getatime(full_path)
            if atime < cutoff:
                app.old_files.append({
                    "path": full_path,
                    "atime": atime,
                    "size": os.path.getsize(full_path)
                })
        except Exception as e:
            logging.warning(f"Não foi possível obter informações do ficheiro {full_path}: {e}")
            continue
        finally:
            if i % 100 == 0:
                app.after(0, app.update_progress_value, i)
                
    app.after(0, app.update_old_files_view)

def run_big_files_analysis(app: 'FinalDiskAnalyzerApp', path: str, top_n: int = 50) -> None:
    """
    Identifica os N maiores ficheiros num diretório e subdiretórios.
    """
    files_info = []
    all_files = [os.path.join(dp, f) for dp, dn, fn in os.walk(path) for f in fn]
    
    app.after(0, app.set_determinate_progress, len(all_files))
    
    for i, full_path in enumerate(all_files):
        try:
            size = os.path.getsize(full_path)
            mtime = os.path.getmtime(full_path)
            files_info.append({"path": full_path, "name": os.path.basename(full_path), "size": size, "mtime": mtime})
        except (PermissionError, FileNotFoundError):
            continue
        finally:
            if i % 100 == 0:
                app.after(0, app.update_progress_value, i)
    
    files_info.sort(key=lambda x: x["size"], reverse=True)
    app.big_files = files_info[:top_n]
    
    app.after(0, app.update_big_files_view)

def compute_storage_summary(app: 'FinalDiskAnalyzerApp') -> None:
    """
    Calcula e apresenta estatísticas resumidas do diretório atual.
    """
    # *** CORREÇÃO AQUI ***
    # Chamada direta à função, sem o prefixo do módulo.
    if app.df_folders.empty and app.df_files.empty:
        run_quick_analysis(app, app.current_path.get())
        return

    all_content = pd.concat([app.df_folders, app.df_files], ignore_index=True)
    if all_content.empty:
        app.storage_summary = {}
        app.after(0, app.update_storage_summary_view)
        return

    total_size = all_content['size'].sum()
    count = all_content.shape[0]
    avg_size = total_size / count if count else 0

    app.storage_summary = {
        "total_files": count,
        "total_size_gb": total_size / (1024**3),
        "avg_size_mb": avg_size / (1024**2)
    }
    app.after(0, app.update_storage_summary_view)
