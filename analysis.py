# analysis.py (versão com varredura robusta)
import os
import time
import logging
import pandas as pd
from tkinter import messagebox
from typing import List, Dict, TYPE_CHECKING
import i18n

if TYPE_CHECKING:
    from ui import FinalDiskAnalyzerApp

from utils import calculate_quick_hash

_ = i18n.get_text

def run_full_scan_and_analyze(app: 'FinalDiskAnalyzerApp', path: str, analyses: Dict[str, bool], params: Dict) -> None:
    """
    Função mestra que percorre o disco UMA VEZ usando o robusto os.walk,
    recolhe os dados e depois executa as análises selecionadas em memória.
    """
    all_files_data = []
    
    try:
        logging.info(f"Iniciando varredura robusta em: {path}")
        app.after(0, app.set_determinate_progress, 0) # Modo indeterminado

        def handle_error(e):
            """Função para ser chamada quando os.walk encontra um erro."""
            logging.warning(f"Erro ao aceder a {e.filename}: {e.strerror}")

        # --- ETAPA 1: PERCORRER O DISCO COM OS.WALK (ROBUSTO) ---
        for dirpath, _, filenames in os.walk(path, onerror=handle_error):
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                try:
                    stat = os.stat(full_path)
                    all_files_data.append({
                        "path": full_path,
                        "name": filename,
                        "size": stat.st_size,
                        "mtime": stat.st_mtime,
                        "atime": stat.st_atime,
                        "ext": os.path.splitext(filename)[1].lower() or '.sem_extensao'
                    })
                except (PermissionError, FileNotFoundError) as e:
                    logging.warning(f"Ignorando ficheiro {full_path}: {e}")
                    continue
        
        logging.info(f"Varredura concluída. {len(all_files_data)} ficheiros encontrados.")
        df_all_files = pd.DataFrame(all_files_data)

    except Exception as e:
        logging.error(f"Erro fatal durante a varredura do disco: {e}", exc_info=True)
        app.after(0, lambda: messagebox.showerror(_("export_error_title"), _("export_error_message")))
        return
    
    # --- ETAPA 2: EXECUTAR ANÁLISES EM MEMÓRIA ---
    if not df_all_files.empty:
        app.df_files = df_all_files[df_all_files['path'].apply(lambda p: os.path.dirname(p) == path)]
        try:
            folder_paths = [d.path for d in os.scandir(path) if d.is_dir()]
            folder_data = []
            for folder_path in folder_paths:
                size = df_all_files[df_all_files['path'].str.startswith(folder_path)]['size'].sum()
                if size > 0:
                    try:
                        stat = os.stat(folder_path)
                        folder_data.append({
                            'name': os.path.basename(folder_path), 'size': size,
                            'mtime': stat.st_mtime, 'path': folder_path, 'ext': '.sem_extensao'
                        })
                    except (PermissionError, FileNotFoundError): continue
            app.df_folders = pd.DataFrame(folder_data)
        except (PermissionError, OSError) as e:
            logging.warning(f"Não foi possível listar as subpastas de {path}: {e}")
            app.df_folders = pd.DataFrame()
    else:
        app.df_files = pd.DataFrame()
        app.df_folders = pd.DataFrame()

    app.after(0, app.update_quick_analysis_view)

    if analyses.get("duplicates"): run_duplicate_analysis(app, df_all_files)
    if analyses.get("old_files"): run_old_files_analysis(app, df_all_files, params.get("days_old", 180))
    if analyses.get("big_files"): run_big_files_analysis(app, df_all_files, params.get("top_n", 50))
    compute_storage_summary(app, df_all_files)


def run_duplicate_analysis(app: 'FinalDiskAnalyzerApp', df: pd.DataFrame):
    if df.empty:
        logging.warning("DataFrame vazio passado para run_duplicate_analysis. A ignorar.")
        app.duplicate_groups = []
        app.after(0, app.update_duplicates_view); return
    logging.info("Iniciando análise de duplicados em memória.")
    files_by_size = df[df['size'] > 1024].groupby('size')['path'].apply(list).to_dict()
    app.duplicate_groups = []
    potential_dups = {s: files for s, files in files_by_size.items() if len(files) > 1}
    for _, files in potential_dups.items():
        hashes: Dict[str, List[str]] = {}
        for file in files:
            h = calculate_quick_hash(file)
            if h: hashes.setdefault(h, []).append(file)
        for h, dup_files in hashes.items():
            if len(dup_files) > 1: app.duplicate_groups.append(dup_files)
    app.after(0, app.update_duplicates_view)

def run_old_files_analysis(app: 'FinalDiskAnalyzerApp', df: pd.DataFrame, days: int):
    if df.empty:
        logging.warning("DataFrame vazio passado para run_old_files_analysis. A ignorar.")
        app.old_files = []
        app.after(0, app.update_old_files_view); return
    logging.info(f"Iniciando análise de ficheiros com mais de {days} dias em memória.")
    cutoff = time.time() - (days * 86400)
    old_files_df = df[df['atime'] < cutoff]
    app.old_files = old_files_df.to_dict('records')
    app.after(0, app.update_old_files_view)

def run_big_files_analysis(app: 'FinalDiskAnalyzerApp', df: pd.DataFrame, top_n: int):
    if df.empty:
        logging.warning("DataFrame vazio passado para run_big_files_analysis. A ignorar.")
        app.big_files = []
        app.after(0, app.update_big_files_view); return
    logging.info(f"Iniciando análise dos {top_n} maiores ficheiros em memória.")
    big_files_df = df.nlargest(top_n, 'size')
    app.big_files = big_files_df.to_dict('records')
    app.after(0, app.update_big_files_view)

def compute_storage_summary(app: 'FinalDiskAnalyzerApp', df: pd.DataFrame):
    logging.info("Calculando resumo em memória.")
    if df.empty:
        app.storage_summary = {}
    else:
        total_size = df['size'].sum()
        count = len(df)
        avg_size = total_size / count if count else 0
        app.storage_summary = {
            "total_files": count,
            "total_size_gb": total_size / (1024**3),
            "avg_size_mb": avg_size / (1024**2)
        }
    app.after(0, app.update_storage_summary_view)
