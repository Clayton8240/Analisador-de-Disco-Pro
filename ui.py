# ui.py
import os
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import threading
import sys
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime
import time
import zipfile
import logging
from typing import Optional

# Importa a lógica de análise do outro módulo
import analysis

class FinalDiskAnalyzerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # ... (código de inicialização, cores, fontes, variáveis de estado igual ao anterior) ...
        self.title("Analisador de Disco Pro - v9.0 Modular")
        # ...

    # ... (Todas as funções `create_*` e `setup_styles` permanecem aqui) ...

    # --- FUNÇÕES DE GESTÃO DE THREADS E ESTADO DA UI ---
    def set_ui_busy(self, is_busy: bool) -> None:
        """Ativa/desativa a UI e muda o cursor durante operações longas."""
        # ... (código igual, sem alterações) ...
        
    def threaded_task(self, func, *args) -> None:
        """Wrapper para executar uma função numa thread com gestão de UI."""
        self.set_ui_busy(True)
        # O primeiro argumento para as funções de análise é sempre a própria instância da app
        thread = threading.Thread(target=self.run_task_wrapper, args=(func, self, *args), daemon=True)
        thread.start()

    def run_task_wrapper(self, func, *args) -> None:
        """Wrapper que executa a função e garante que a UI é reativada."""
        try:
            func(*args)
        except Exception as e:
            logging.error(f"Erro na thread da função {func.__name__}", exc_info=True)
            self.after(0, lambda: messagebox.showerror("Erro Inesperado", f"Ocorreu um erro. Verifique 'disk_analyzer.log'."))
        finally:
            self.after(0, self.set_ui_busy, False)

    # --- FUNÇÕES DE EVENTOS QUE INICIAM AS ANÁLISES ---
    def on_folder_select(self, event) -> None:
        if not self.tree.selection(): return
        folder_id = self.tree.selection()[0]
        folder_path = self.tree.item(folder_id)['values'][0]
        self.current_path.set(folder_path)
        self.reset_view_state()
        self.lbl_status.pack(pady=50)
        self.lbl_status.config(text=f"Analisando '{os.path.basename(folder_path)}'...")
        # Chama a função do módulo 'analysis'
        self.threaded_task(analysis.run_quick_analysis, folder_path)

    def start_duplicate_search(self) -> None:
        path = self.current_path.get()
        if not os.path.isdir(path): return
        self.get_status_label().config(text="Procurando duplicados...")
        self.notebook.select(self.duplicates_tab)
        # Chama a função do módulo 'analysis'
        self.threaded_task(analysis.run_duplicate_analysis, path)

    def start_old_files_search(self) -> None:
        days = simpledialog.askinteger("Filtro de Ficheiros Antigos", "Identificar ficheiros não acedidos há mais de (dias):", initialvalue=180, minvalue=1, parent=self)
        if not days: return
        path = self.current_path.get()
        if not os.path.isdir(path): return
        self.get_status_label().config(text=f"Procurando ficheiros com mais de {days} dias...")
        self.notebook.select(self.old_files_tab)
        # Chama a função do módulo 'analysis'
        self.threaded_task(analysis.run_old_files_analysis, path, days)
        
    # --- FUNÇÕES DE ATUALIZAÇÃO DA UI (Callbacks) ---
    def update_quick_analysis_view(self):
        self.btn_find_duplicates.config(state='normal'); self.btn_export.config(state='normal'); self.btn_find_old_files.config(state='normal')
        all_content = pd.concat([self.df_folders, self.df_files], ignore_index=True)
        if all_content.empty: self.lbl_status.config(text="Pasta vazia ou sem conteúdo acessível."); self.set_ui_busy(False); return
        self.apply_filters()
        self.update_pie_chart()
        
    def update_duplicates_view(self):
        self.get_status_label().config(text="")
        self.populate_duplicates_table()
        if self.duplicate_groups:
            self.btn_delete_duplicates.config(state='normal'); messagebox.showinfo("Duplicados Encontrados", f"Foram encontrados {len(self.duplicate_groups)} grupos de ficheiros duplicados.")
        else: messagebox.showinfo("Nenhum Duplicado", "Não foram encontrados ficheiros duplicados nesta pasta.")

    def update_old_files_view(self):
        self.get_status_label().config(text="")
        self.populate_old_files_table()
        if self.old_files:
            self.btn_compress_old_files.config(state='normal')
            messagebox.showinfo("Análise Concluída", f"Foram encontrados {len(self.old_files)} ficheiros não acedidos no período definido.")
        else:
            messagebox.showinfo("Análise Concluída", "Não foram encontrados ficheiros antigos neste diretório.")
    # ... [O RESTANTE DO CÓDIGO DA CLASSE `FinalDiskAnalyzerApp` VAI AQUI] ...
    # (Copie e cole todo o restante código da classe da versão anterior para este ficheiro)
