import os
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import threading
import sys
import subprocess
import pandas as pd
import hashlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime
import time
import zipfile
import logging

# -------------------------------------------------------------------
# --- CONFIGURAÇÃO INICIAL DO LOGGING CORPORATIVO ---
# -------------------------------------------------------------------
logging.basicConfig(filename='disk_analyzer.log', 
                    level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    encoding='utf-8')

# -------------------------------------------------------------------
# --- CLASSE FINAL E CONSOLIDADA DA APLICAÇÃO ---
# -------------------------------------------------------------------
class FinalDiskAnalyzerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # --- DEFINIÇÃO DA IDENTIDADE VISUAL ---
        self.COLOR_BACKGROUND = '#2E2E2E'
        self.COLOR_CONTENT_BG = '#3C3C3C'
        self.COLOR_TEXT = '#F5F5F5'
        self.COLOR_ACCENT = '#007ACC'
        self.COLOR_SUCCESS = '#2E7D32'
        self.FONT_DEFAULT = ("Segoe UI", 10)
        self.FONT_LABEL = ("Segoe UI", 11, "bold")

        # --- Configuração da Janela Principal ---
        self.title("Analisador de Disco Pro")
        self.geometry("1200x800")
        self.configure(background=self.COLOR_BACKGROUND)

        try:
            self.iconbitmap('app_icon.ico') 
        except tk.TclError:
            logging.warning("Ficheiro 'app_icon.ico' não encontrado.")

        self.setup_styles()

        # --- Variáveis de Estado ---
        self.df_files = pd.DataFrame()
        self.df_folders = pd.DataFrame()
        self.duplicate_groups = []
        self.old_files = []
        self.current_path = tk.StringVar(value="Selecione uma pasta na árvore de navegação")
        self.filter_text_var = tk.StringVar()
        self.filter_min_size_var = tk.StringVar()
        self.filter_max_size_var = tk.StringVar()
        self.filter_unit_var = tk.StringVar(value="MB")
        self.category_vars = {}
        self.category_map = {
            "Imagens": ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg'],
            "Música": ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.wma', '.m4a'],
            "Vídeos": ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'],
            "Documentos": ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.rtf', '.csv'],
            "Compactados": ['.zip', '.rar', '.7z', '.tar', '.gz', '.iso', '.jar'],
            "Sistema/Exec.": ['.exe', '.dll', '.sys', '.ini', '.drv', '.bat', '.sh']
        }
        
        # --- Criação da Interface Gráfica ---
        self.create_interface()
        
        # --- Eventos, População e Inicialização Final ---
        self.tree.bind('<<TreeviewOpen>>', self.on_tree_open)
        self.tree.bind('<<TreeviewSelect>>', self.on_folder_select)
        self.populate_root_nodes()
        self.create_context_menu()
        
        logging.info("Aplicação iniciada com sucesso.")

    def setup_styles(self):
        """Configura todos os estilos personalizados para a aplicação."""
        style = ttk.Style(self)
        style.theme_use('clam')

        style.configure('.', background=self.COLOR_BACKGROUND, foreground=self.COLOR_TEXT, 
                        fieldbackground=self.COLOR_CONTENT_BG, font=self.FONT_DEFAULT)
        style.map('.', background=[('active', self.COLOR_ACCENT)], foreground=[('active', self.COLOR_TEXT)])
        style.configure('TFrame', background=self.COLOR_BACKGROUND)
        style.configure('TLabel', background=self.COLOR_BACKGROUND, foreground=self.COLOR_TEXT)
        style.configure('TLabelframe', background=self.COLOR_BACKGROUND, bordercolor=self.COLOR_TEXT)
        style.configure('TLabelframe.Label', background=self.COLOR_BACKGROUND, foreground=self.COLOR_TEXT, font=self.FONT_LABEL)
        style.configure('TButton', background=self.COLOR_CONTENT_BG, foreground=self.COLOR_TEXT, font=self.FONT_DEFAULT, padding=5)
        style.map('TButton', background=[('active', self.COLOR_ACCENT)])
        style.configure('Accent.TButton', background=self.COLOR_ACCENT, font=('Segoe UI', 10, 'bold'))
        style.map('Accent.TButton', background=[('active', self.COLOR_SUCCESS)])
        style.configure('Treeview', rowheight=25, fieldbackground=self.COLOR_CONTENT_BG, background=self.COLOR_CONTENT_BG, foreground=self.COLOR_TEXT)
        style.map('Treeview', background=[('selected', self.COLOR_ACCENT)])
        style.configure('Treeview.Heading', background='#2A2A2A', font=('Segoe UI', 10, 'bold'), padding=5)
        style.configure('TNotebook', background=self.COLOR_BACKGROUND, tabmargins=[2, 5, 2, 0])
        style.configure('TNotebook.Tab', background=self.COLOR_CONTENT_BG, foreground=self.COLOR_TEXT, padding=[10, 5])
        style.map('TNotebook.Tab', background=[('selected', self.COLOR_ACCENT)], foreground=[('selected', self.COLOR_TEXT)])
        style.configure('custom.Horizontal.TProgressbar', troughcolor=self.COLOR_CONTENT_BG, background=self.COLOR_ACCENT)

    def create_interface(self):
        """Cria e organiza todos os widgets da aplicação."""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill='both', expand=True)
        
        # -- Layout Principal --
        self.paned_window = ttk.PanedWindow(main_frame, orient='horizontal')
        self.paned_window.pack(fill='both', expand=True)

        # Painel Esquerdo: Navegação
        nav_frame = ttk.LabelFrame(self.paned_window, text="Navegação", padding=5)
        self.paned_window.add(nav_frame, weight=1)
        self.tree = ttk.Treeview(nav_frame, show="tree headings")
        self.tree.heading("#0", text="Diretórios")
        tree_scrollbar = ttk.Scrollbar(nav_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        tree_scrollbar.pack(side='right', fill='y')
        self.tree.pack(fill='both', expand=True)
        
        # Painel Direito: Análise
        self.view_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.view_frame, weight=3)
        self.create_view_panel()
        
    def create_view_panel(self):
        """Cria todos os widgets do painel direito."""
        # Ações Principais
        action_frame = ttk.Frame(self.view_frame)
        action_frame.pack(fill='x', pady=5)
        ttk.Label(action_frame, text="Pasta Atual:", font=self.FONT_LABEL).pack(side='left')
        path_label = ttk.Label(action_frame, textvariable=self.current_path, font=('Segoe UI', 10, 'italic'), relief='sunken', padding=5)
        path_label.pack(side='left', fill='x', expand=True, padx=10)
        
        self.btn_find_duplicates = ttk.Button(action_frame, text="Procurar Duplicados", command=self.start_duplicate_search, state='disabled')
        self.btn_find_duplicates.pack(side='left', padx=(0,5))
        self.btn_find_old_files = ttk.Button(action_frame, text="Procurar Ficheiros Antigos", command=self.start_old_files_search, state='disabled')
        self.btn_find_old_files.pack(side='left')

        # Abas de Resultados
        self.notebook = ttk.Notebook(self.view_frame)
        self.notebook.pack(fill='both', expand=True, pady=5)
        
        self.chart_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.chart_tab, text="Gráfico de Espaço")
        self.files_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.files_tab, text="Lista Detalhada")
        self.duplicates_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.duplicates_tab, text="Duplicados")
        self.old_files_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.old_files_tab, text="Ficheiros Antigos")

        self.lbl_status = ttk.Label(self.chart_tab, text="Selecione uma pasta para iniciar a análise.", font=('Segoe UI', 14))
        self.lbl_status.pack(pady=50)
        self.fig_canvas = None
        
        # Conteúdo das abas
        self.create_filter_panel(self.files_tab)
        self.create_file_list_table(self.files_tab)
        self.create_duplicates_table(self.duplicates_tab)
        self.create_old_files_table(self.old_files_tab)

    def create_filter_panel(self, parent_tab):
        filter_frame = ttk.LabelFrame(parent_tab, text="Filtros", padding=10)
        filter_frame.pack(fill='x', padx=5, pady=5)
        # ... (código igual)
        
    def create_file_list_table(self, parent_tab):
        frame = ttk.Frame(parent_tab)
        frame.pack(fill='both', expand=True, padx=5, pady=5)
        cols = ("Nome", "Tamanho (MB)", "Data de Modificação", "Caminho Completo")
        self.files_tree = ttk.Treeview(frame, columns=cols, show='headings')
        for col in cols: self.files_tree.heading(col, text=col)
        self.files_tree.column("Nome", width=250); self.files_tree.column("Tamanho (MB)", anchor='e', width=120)
        self.files_tree.column("Data de Modificação", width=150); self.files_tree.column("Caminho Completo", width=400)
        v_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.files_tree.yview)
        h_scroll = ttk.Scrollbar(frame, orient="horizontal", command=self.files_tree.xview)
        self.files_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.pack(side='right', fill='y'); h_scroll.pack(side='bottom', fill='x')
        self.files_tree.pack(fill='both', expand=True)
        self.files_tree.bind("<Double-1>", self.on_double_click_item)

    def on_double_click_item(self, event):
        self.open_file_location()
        
    
    def create_filter_panel(self, parent_tab):
        filter_frame = ttk.LabelFrame(parent_tab, text="Filtros", padding=10); filter_frame.pack(fill='x', padx=5, pady=5)
        filter_frame.columnconfigure(1, weight=1)
        left_frame = ttk.Frame(filter_frame); left_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        ttk.Label(left_frame, text="Nome/Caminho:").pack(anchor='w'); ttk.Entry(left_frame, textvariable=self.filter_text_var).pack(anchor='w', fill='x')
        size_frame = ttk.Frame(left_frame); size_frame.pack(anchor='w', pady=(10,0))
        ttk.Label(size_frame, text="Tamanho: >").pack(side='left'); ttk.Entry(size_frame, textvariable=self.filter_min_size_var, width=8).pack(side='left')
        ttk.Label(size_frame, text="<").pack(side='left', padx=(5,0)); ttk.Entry(size_frame, textvariable=self.filter_max_size_var, width=8).pack(side='left')
        ttk.Combobox(size_frame, textvariable=self.filter_unit_var, values=["KB", "MB", "GB"], width=4, state="readonly").pack(side='left', padx=5)
        right_frame = ttk.Frame(filter_frame); right_frame.grid(row=0, column=1, sticky='nsew')
        ttk.Label(right_frame, text="Categorias:").pack(anchor='w'); types_frame = ttk.Frame(right_frame); types_frame.pack(anchor='w', pady=5)
        col, row = 0, 0
        for category in self.category_map.keys():
            var = tk.BooleanVar(); cb = ttk.Checkbutton(types_frame, text=category, variable=var); cb.grid(row=row, column=col, sticky='w', padx=5)
            self.category_vars[category] = var; col += 1
            if col > 2: col = 0; row += 1
        action_frame = ttk.Frame(left_frame); action_frame.pack(anchor='w', pady=(15,0))
        self.btn_apply_filters = ttk.Button(action_frame, text="Aplicar Filtros", command=self.apply_filters); self.btn_apply_filters.pack(side='left')
        self.btn_clear_filters = ttk.Button(action_frame, text="Limpar", command=self.clear_filters); self.btn_clear_filters.pack(side='left', padx=5)
    def create_duplicates_table(self, parent_tab):
        frame = ttk.Frame(parent_tab); frame.pack(fill='both', expand=True, padx=5, pady=5)
        cols = ("Ficheiro / Grupo", "Tamanho (MB)"); self.duplicates_tree = ttk.Treeview(frame, columns=cols, show='headings')
        self.duplicates_tree.heading("Ficheiro / Grupo", text="Ficheiro / Grupo"); self.duplicates_tree.heading("Tamanho (MB)", text="Tamanho (MB)"); self.duplicates_tree.column("Tamanho (MB)", anchor='e')
        v_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.duplicates_tree.yview); h_scroll = ttk.Scrollbar(frame, orient="horizontal", command=self.duplicates_tree.xview)
        self.duplicates_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set); v_scroll.pack(side='right', fill='y'); h_scroll.pack(side='bottom', fill='x'); self.duplicates_tree.pack(fill='both', expand=True)
        btn_frame = ttk.Frame(parent_tab); btn_frame.pack(fill='x', padx=5)
        self.btn_delete_duplicates = ttk.Button(btn_frame, text="Apagar Selecionados", command=self.delete_selected_duplicates, state='disabled'); self.btn_delete_duplicates.pack(side='left', pady=5)
        self.btn_export = ttk.Button(btn_frame, text="Exportar Resultados", command=self.export_to_excel, state='disabled'); self.btn_export.pack(side='right', pady=5)
    def create_old_files_table(self, parent_tab):
        frame = ttk.Frame(parent_tab); frame.pack(fill='both', expand=True, padx=5, pady=5)
        cols = ("Ficheiro", "Tamanho (MB)", "Último Acesso"); self.old_files_tree = ttk.Treeview(frame, columns=cols, show='headings')
        for col in cols: self.old_files_tree.heading(col, text=col)
        self.old_files_tree.column("Ficheiro", width=500); self.old_files_tree.column("Tamanho (MB)", anchor='e', width=120); self.old_files_tree.column("Último Acesso", anchor='center', width=150)
        v_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.old_files_tree.yview); v_scroll.pack(side='right', fill='y')
        self.old_files_tree.configure(yscrollcommand=v_scroll.set); self.old_files_tree.pack(fill='both', expand=True)
        btn_frame = ttk.Frame(parent_tab); btn_frame.pack(fill='x', padx=5)
        self.btn_compress_old_files = ttk.Button(btn_frame, text="Comprimir Selecionados para .zip", command=self.compress_selected_old_files, state='disabled'); self.btn_compress_old_files.pack(side='left', pady=5)
    def create_context_menu(self):
        self.context_menu = tk.Menu(self, tearoff=0); self.context_menu.add_command(label="Abrir Localização", command=self.open_file_location); self.context_menu.add_separator(); self.context_menu.add_command(label="Abrir Ficheiro", command=self.open_file)
        self.files_tree.bind("<Button-3>", self.show_context_menu); self.tree.bind("<Button-3>", self.show_nav_context_menu)
    def show_context_menu(self, event):
        tree = event.widget; item_id = tree.identify_row(event.y)
        if item_id:
            tree.selection_set(item_id); item_path = tree.item(item_id)['values'][3]
            if os.path.isdir(item_path): self.context_menu.entryconfig("Abrir Ficheiro", state="disabled")
            else: self.context_menu.entryconfig("Abrir Ficheiro", state="normal")
            self.context_menu.post(event.x_root, event.y_root)
    def show_nav_context_menu(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self.tree.selection_set(item_id); self.context_menu.entryconfig("Abrir Ficheiro", state="disabled"); self.context_menu.entryconfig("Abrir Localização", label="Abrir Pasta"); self.context_menu.post(event.x_root, event.y_root)
    def open_file_location(self):
        try:
            tree = self.focus_get()
            if not isinstance(tree, ttk.Treeview): return
            item_id = tree.selection()[0]
            if not item_id: return
            values = tree.item(item_id)['values']
            item_path = values[0] if tree is self.tree else values[3]
            folder_path = os.path.dirname(item_path) if os.path.isfile(item_path) else item_path
            if sys.platform == "win32": os.startfile(folder_path)
            elif sys.platform == "darwin": subprocess.run(["open", folder_path])
            else: subprocess.run(["xdg-open", folder_path])
        except Exception as e: messagebox.showerror("Erro", f"Não foi possível abrir a pasta:\n{e}")
    def open_file(self):
        try:
            tree = self.focus_get()
            if tree is not self.files_tree: return
            item_id = tree.selection()[0]
            if not item_id: return
            file_path = tree.item(item_id)['values'][3]
            if os.path.isfile(file_path):
                if sys.platform == "win32": os.startfile(file_path)
                elif sys.platform == "darwin": subprocess.run(["open", file_path])
                else: subprocess.run(["xdg-open", file_path])
        except Exception as e: messagebox.showerror("Erro", f"Não foi possível abrir o ficheiro:\n{e}")
    def set_ui_busy(self, is_busy):
        cursor = "watch" if is_busy else ""
        self.config(cursor=cursor)
        state = 'disabled' if is_busy else 'normal'
        if is_busy: self.tree.unbind("<<TreeviewSelect>>")
        else: self.tree.bind("<<TreeviewSelect>>", self.on_folder_select)
        self.btn_find_duplicates.config(state=state); self.btn_find_old_files.config(state=state)
        if not is_busy and not os.path.isdir(self.current_path.get()):
            self.btn_find_duplicates.config(state='disabled'); self.btn_find_old_files.config(state='disabled')
        self.update_idletasks()
    def threaded_task(self, func, *args):
        self.set_ui_busy(True)
        thread = threading.Thread(target=self.run_task_wrapper, args=(func, *args), daemon=True)
        thread.start()
    def run_task_wrapper(self, func, *args):
        try: func(*args)
        except Exception:
            logging.error(f"Erro na thread da função {func.__name__}", exc_info=True)
            self.after(0, lambda: messagebox.showerror("Erro Inesperado", "Ocorreu um erro. Verifique 'disk_analyzer.log'."))
        finally:
            self.after(0, self.set_ui_busy, False)
    def start_old_files_search(self):
        days = simpledialog.askinteger("Filtro de Ficheiros Antigos", "Identificar ficheiros não acedidos há mais de (dias):", initialvalue=180, minvalue=1, parent=self)
        if not days: return
        path = self.current_path.get()
        if not os.path.isdir(path): return
        self.get_status_label().config(text=f"Procurando ficheiros com mais de {days} dias...")
        self.notebook.select(self.old_files_tab)
        self.threaded_task(self.run_old_files_analysis, path, days)
    def run_old_files_analysis(self, path, days):
        cutoff = time.time() - (days * 86400)
        self.old_files = []
        for dirpath, _, filenames in os.walk(path, onerror=lambda e: logging.warning(f"Erro ao aceder a {e.filename}: {e.strerror}")):
            for f in filenames:
                full_path = os.path.join(dirpath, f)
                try:
                    atime = os.path.getatime(full_path)
                    if atime < cutoff: self.old_files.append({"path": full_path, "atime": atime, "size": os.path.getsize(full_path)})
                except Exception as e: logging.warning(f"Não foi possível obter informações do ficheiro {full_path}: {e}")
        self.after(0, self.update_old_files_view)
    def update_old_files_view(self):
        self.get_status_label().config(text="")
        self.populate_old_files_table()
        if self.old_files:
            self.btn_compress_old_files.config(state='normal')
            messagebox.showinfo("Análise Concluída", f"Foram encontrados {len(self.old_files)} ficheiros não acedidos no período definido.")
        else:
            messagebox.showinfo("Análise Concluída", "Não foram encontrados ficheiros antigos neste diretório.")
    def compress_selected_old_files(self):
        selected_iids = self.old_files_tree.selection()
        if not selected_iids: messagebox.showwarning("Nenhum Ficheiro", "Selecione os ficheiros a comprimir."); return
        files_to_compress = [self.old_files_tree.item(iid)['values'][0] for iid in selected_iids]
        total_size = sum(os.path.getsize(f) for f in files_to_compress if os.path.exists(f))
        save_path = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("ZIP archive", "*.zip")], title="Guardar ficheiro ZIP")
        if not save_path: return
        save_dir = os.path.dirname(save_path)
        try:
            _, _, free_space = shutil.disk_usage(save_dir)
            if total_size >= free_space:
                logging.error(f"Espaço insuficiente. Necessário: {total_size}, Disponível: {free_space}")
                messagebox.showerror("Espaço Insuficiente", f"Espaço necessário: {total_size/(1024*1024):.2f} MB\nEspaço disponível: {free_space/(1024*1024):.2f} MB")
                return
        except FileNotFoundError: messagebox.showerror("Caminho Inválido", "O diretório para salvar o arquivo não existe."); return
        if not messagebox.askyesno("Confirmar Arquivamento", f"Comprimir {len(selected_iids)} ficheiro(s) e APAGAR os originais?"): return
        self.threaded_task(self.run_compression_and_deletion, files_to_compress, save_path)
    def run_compression_and_deletion(self, file_list, zip_path):
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in file_list:
                    if os.path.exists(file_path): zf.write(file_path, arcname=os.path.basename(file_path))
            logging.info(f"{len(file_list)} ficheiros comprimidos para {zip_path}")
            deleted_count = 0
            for file_path in file_list:
                try: os.remove(file_path); deleted_count += 1
                except Exception: logging.error(f"Falha ao apagar {file_path}", exc_info=True)
            logging.info(f"{deleted_count} de {len(file_list)} ficheiros originais apagados.")
            self.after(0, lambda: messagebox.showinfo("Sucesso", f"{deleted_count} ficheiros foram comprimidos e arquivados."))
            self.after(0, lambda: self.on_folder_select(None)) # Recarrega a vista
        except Exception:
            logging.error(f"Erro fatal durante a compressão para {zip_path}", exc_info=True)
            self.after(0, lambda: messagebox.showerror("Erro de Compressão", "Ocorreu um erro. Verifique 'disk_analyzer.log'."))
    def get_status_label(self):
        try:
            current_tab_text = self.notebook.tab(self.notebook.select(), "text")
            if current_tab_text == "Duplicados": return ttk.Label(self.duplicates_tab)
            elif current_tab_text == "Ficheiros Antigos": return ttk.Label(self.old_files_tab)
            else: return self.lbl_status
        except tk.TclError: return self.lbl_status
    def on_folder_select(self, event):
        if not self.tree.selection(): return
        folder_id = self.tree.selection()[0]; folder_path = self.tree.item(folder_id)['values'][0]
        self.current_path.set(folder_path); self.reset_view_state()
        self.lbl_status.pack(pady=50); self.lbl_status.config(text=f"Analisando '{os.path.basename(folder_path)}'...")
        self.threaded_task(self.run_quick_analysis, folder_path)
    def run_quick_analysis(self, path):
        folders_data, files_data = [], []
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                try:
                    mtime = os.path.getmtime(item_path); _, ext = os.path.splitext(item); ext = ext.lower() if ext else '.sem_extensao'
                    if os.path.isdir(item_path):
                        size = sum(os.path.getsize(os.path.join(dp, fn)) for dp, _, fns in os.walk(item_path, onerror=lambda e:None) for fn in fns)
                        if size > 0: folders_data.append({'name': item, 'size': size, 'mtime': mtime, 'path': item_path, 'ext': ext})
                    else:
                        size = os.path.getsize(item_path)
                        if size > 0: files_data.append({'name': item, 'size': size, 'mtime': mtime, 'path': item_path, 'ext': ext})
                except (PermissionError, FileNotFoundError): continue
        except PermissionError as e:
            logging.error(f"Acesso negado ao ler {path}", exc_info=True)
            self.after(0, lambda: messagebox.showerror("Erro de Acesso", f"Não foi possível ler o conteúdo de:\n{path}")); return
        self.df_folders = pd.DataFrame(folders_data); self.df_files = pd.DataFrame(files_data)
        self.after(0, self.update_quick_analysis_view)
    def update_quick_analysis_view(self):
        self.btn_find_duplicates.config(state='normal'); self.btn_export.config(state='normal'); self.btn_find_old_files.config(state='normal')
        all_content = pd.concat([self.df_folders, self.df_files], ignore_index=True)
        if all_content.empty: self.lbl_status.config(text="Pasta vazia ou sem conteúdo acessível."); self.set_ui_busy(False); return
        self.apply_filters()
        self.update_pie_chart()
    def update_pie_chart(self):
        if self.fig_canvas:
            self.fig_canvas.get_tk_widget().destroy()
        self.lbl_status.pack_forget()

        chart_data = pd.concat([self.df_folders, self.df_files], ignore_index=True)
        if chart_data.empty:
            return

        top_n = 7
        df_plot = chart_data.nlargest(top_n, 'size').copy()
        
        if len(chart_data) > top_n:
            outros_size = chart_data.nsmallest(len(chart_data) - top_n, 'size')['size'].sum()
            outros_row = pd.DataFrame([{'name': 'Outros', 'size': outros_size}])
            df_plot = pd.concat([df_plot, outros_row], ignore_index=True)

        total_size = chart_data['size'].sum()
        if total_size == 0: return

        # Cria as legendas com nomes e percentagens
        labels_for_legend = [f"{row['name']} ({row['size']/total_size:.1%})" for _, row in df_plot.iterrows()]

        # Cria a figura e o eixo
        plt.style.use('seaborn-v0_8-deep')
        fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
        
        # CORREÇÃO: Ajusta o subplot para criar espaço à direita para a legenda
        fig.subplots_adjust(left=0.05, right=0.7)

        # Desenha o gráfico de pizza (donut)
        wedges, _ = ax.pie(df_plot['size'], startangle=90, wedgeprops=dict(width=0.4), radius=1.2)
        
        # Adiciona a legenda no espaço criado
        ax.legend(wedges, labels_for_legend,
                  title="Conteúdo Principal",
                  loc="center left",
                  bbox_to_anchor=(1, 0, 0.5, 1), # Posiciona a legenda fora do gráfico
                  fontsize='medium')
        
        ax.set_title(f"Distribuição de Espaço em '{os.path.basename(self.current_path.get())}'", pad=20, fontdict={'fontsize': 14})
        
        # Desenha no canvas do Tkinter
        self.fig_canvas = FigureCanvasTkAgg(fig, master=self.chart_tab)
        self.fig_canvas.draw()
        self.fig_canvas.get_tk_widget().pack(fill='both', expand=True, padx=5, pady=5)

    def start_duplicate_search(self):
        path = self.current_path.get();
        if not os.path.isdir(path): return
        self.get_status_label().config(text="Procurando duplicados..."); self.notebook.select(self.duplicates_tab)
        self.threaded_task(self.run_duplicate_analysis, path)
    def run_duplicate_analysis(self, path):
        files_by_size = {}
        for dirpath, _, filenames in os.walk(path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                try:
                    size = os.path.getsize(file_path)
                    if size > 1024:
                        if size not in files_by_size: files_by_size[size] = []
                        files_by_size[size].append(file_path)
                except (PermissionError, FileNotFoundError): continue
        self.duplicate_groups = []
        potential_dups = {s: files for s, files in files_by_size.items() if len(files) > 1}
        for size, files in potential_dups.items():
            hashes = {};
            for file in files:
                h = self.calculate_hash(file)
                if h:
                    if h not in hashes: hashes[h] = []
                    hashes[h].append(file)
            for h, dup_files in hashes.items():
                if len(dup_files) > 1: self.duplicate_groups.append(dup_files)
        self.after(0, self.update_duplicates_view)
    def update_duplicates_view(self):
        self.get_status_label().config(text="")
        self.populate_duplicates_table()
        if self.duplicate_groups:
            self.btn_delete_duplicates.config(state='normal'); messagebox.showinfo("Duplicados Encontrados", f"Foram encontrados {len(self.duplicate_groups)} grupos de ficheiros duplicados.")
        else: messagebox.showinfo("Nenhum Duplicado", "Não foram encontrados ficheiros duplicados nesta pasta.")
    def populate_root_nodes(self):
        if sys.platform == "win32":
            import string
            drives = [f'{d}:\\' for d in string.ascii_uppercase if os.path.exists(f'{d}:')];
            for drive in drives: node = self.tree.insert('', 'end', text=drive, values=[drive, 'drive']); self.tree.insert(node, 'end')
        else: root_node = self.tree.insert('', 'end', text="/", values=["/", 'folder']); self.tree.insert(root_node, 'end')
    def on_tree_open(self, event):
        parent_id = self.tree.focus(); parent_path = self.tree.item(parent_id)['values'][0]
        self.tree.delete(*self.tree.get_children(parent_id))
        try:
            for item in os.listdir(parent_path):
                full_path = os.path.join(parent_path, item)
                if os.path.isdir(full_path):
                    try: os.listdir(full_path); node = self.tree.insert(parent_id, 'end', text=item, values=[full_path, 'folder']); self.tree.insert(node, 'end')
                    except PermissionError: continue
        except PermissionError: pass
    def reset_view_state(self):
        if self.fig_canvas: self.fig_canvas.get_tk_widget().destroy()
        self.lbl_status.config(text="Selecione uma pasta à esquerda para analisar."); self.lbl_status.pack(pady=50)
        self.clear_filters(); self.files_tree.delete(*self.files_tree.get_children())
        self.duplicates_tree.delete(*self.duplicates_tree.get_children()); self.old_files_tree.delete(*self.old_files_tree.get_children())
        self.btn_find_duplicates.config(state='disabled'); self.btn_delete_duplicates.config(state='disabled'); self.btn_export.config(state='disabled'); self.btn_find_old_files.config(state='disabled'); self.btn_compress_old_files.config(state='disabled')
    def apply_filters(self):
        unit = self.filter_unit_var.get(); multiplier = {"KB": 1024, "MB": 1024**2, "GB": 1024**3}[unit]
        try: min_size = float(self.filter_min_size_var.get() or 0) * multiplier; max_size = float(self.filter_max_size_var.get() or float('inf')) * multiplier
        except ValueError: messagebox.showerror("Erro de Valor", "Insira apenas números nos campos de tamanho."); return
        texto = self.filter_text_var.get().lower(); exts = []; [exts.extend(self.category_map[cat]) for cat, var in self.category_vars.items() if var.get()]
        all_content = pd.concat([self.df_folders, self.df_files], ignore_index=True)
        if all_content.empty: self.populate_file_list_table(all_content); return
        mask = pd.Series(True, index=all_content.index)
        if texto: mask &= all_content['path'].str.lower().str.contains(texto, na=False)
        if min_size > 0: mask &= all_content['size'] >= min_size
        if max_size != float('inf'): mask &= all_content['size'] <= max_size
        if exts: mask &= all_content['ext'].isin(exts)
        self.populate_file_list_table(all_content[mask])
    def clear_filters(self):
        self.filter_text_var.set(""); self.filter_min_size_var.set(""); self.filter_max_size_var.set("")
        for var in self.category_vars.values(): var.set(False)
        self.apply_filters()
    def populate_file_list_table(self, dataframe):
        self.files_tree.delete(*self.files_tree.get_children())
        for _, row in dataframe.iterrows():
            name = row['name']; size_mb = row['size'] / (1024*1024); mtime = datetime.fromtimestamp(row['mtime']).strftime('%Y-%m-%d %H:%M')
            self.files_tree.insert("", "end", values=(name, f"{size_mb:,.2f}", mtime, row['path']))
    def populate_duplicates_table(self):
        self.duplicates_tree.delete(*self.duplicates_tree.get_children())
        for i, group in enumerate(self.duplicate_groups):
            if not group: continue
            size_mb = os.path.getsize(group[0]) / (1024*1024)
            parent = self.duplicates_tree.insert("", "end", iid=f"G{i}", values=(f"Grupo {i+1} ({len(group)} ficheiros)", f"{size_mb:,.2f}"))
            for file_path in group: self.duplicates_tree.insert(parent, "end", values=(f"  └─ {file_path}", ""))
    def populate_old_files_table(self):
        self.old_files_tree.delete(*self.old_files_tree.get_children())
        self.old_files.sort(key=lambda x: x['atime'])
        for item in self.old_files:
            size_mb = item['size'] / (1024*1024); atime_str = datetime.fromtimestamp(item['atime']).strftime('%Y-%m-%d')
            self.old_files_tree.insert("", "end", values=(item['path'], f"{size_mb:,.2f}", atime_str), iid=item['path'])
    def delete_selected_duplicates(self):
        selected_items = self.duplicates_tree.selection()
        files_to_delete = [self.duplicates_tree.item(item)['values'][0].strip().replace("└─ ", "") for item in selected_items if self.duplicates_tree.parent(item)]
        if not files_to_delete: messagebox.showwarning("Aviso", "Selecione os ficheiros individuais (não os grupos) a apagar."); return
        if messagebox.askyesno("Confirmar", f"Apagar permanentemente {len(files_to_delete)} ficheiros?"):
            for file in files_to_delete:
                try: os.remove(file)
                except Exception as e: logging.error(f"Falha ao apagar ficheiro duplicado {file}", exc_info=True)
            messagebox.showinfo("Concluído", f"{len(files_to_delete)} ficheiros apagados."); self.on_folder_select(None)
    def export_to_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if not path: return
        try:
            with pd.ExcelWriter(path) as writer:
                all_content = pd.concat([self.df_folders, self.df_files], ignore_index=True)
                if not all_content.empty: all_content.to_excel(writer, sheet_name="Conteúdo da Pasta", index=False)
                if self.duplicate_groups: pd.DataFrame(self.duplicate_groups).to_excel(writer, sheet_name="Ficheiros Duplicados", index=False)
                if self.old_files: pd.DataFrame(self.old_files).to_excel(writer, sheet_name="Ficheiros Antigos", index=False)
            logging.info(f"Resultados exportados com sucesso para {path}")
            messagebox.showinfo("Sucesso", f"Resultados exportados para:\n{path}")
        except Exception as e:
            logging.error(f"Erro ao exportar para Excel em {path}", exc_info=True)
            messagebox.showerror("Erro", f"Erro ao exportar. Verifique 'disk_analyzer.log'.")
    def calculate_hash(self, path):
        h = hashlib.sha1()
        try:
            with open(path, 'rb') as f:
                while True:
                    chunk = f.read(h.block_size);
                    if not chunk: break
                    h.update(chunk)
            return h.hexdigest()
        except: return None
        
# -------------------------------------------------------------------
# --- PONTO DE ENTRADA DA APLICAÇÃO ---
# -------------------------------------------------------------------
if __name__ == "__main__":
    app = FinalDiskAnalyzerApp()
    app.mainloop()

