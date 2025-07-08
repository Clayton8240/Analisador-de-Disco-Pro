# ui.py (versão com a correção no layout dos botões)
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

import analysis
import utils
import i18n
import themes

_ = i18n.get_text

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class SplashScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.splash_image = tk.PhotoImage(file=resource_path("splash_screen.png"))
        width, height = self.splash_image.width(), self.splash_image.height()
        self.overrideredirect(True)
        screen_width, screen_height = self.winfo_screenwidth(), self.winfo_screenheight()
        x = (screen_width / 2) - (width / 2)
        y = (screen_height / 2) - (height / 2)
        self.geometry(f'{width}x{height}+{int(x)}+{int(y)}')
        tk.Label(self, image=self.splash_image).pack()
        s = ttk.Style()
        s.configure("Splash.Horizontal.TProgressbar", background='#007ACC')
        self.progress = ttk.Progressbar(self, orient="horizontal", style="Splash.Horizontal.TProgressbar", length=100, mode="indeterminate")
        self.progress.pack(fill='x', padx=10, pady=10)
        self.progress.start(10)
        self.update()

class FinalDiskAnalyzerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        splash = SplashScreen(self)
        self.load_theme_colors()
        self.title(_("title"))
        self.geometry("1200x800")
        self.configure(background=self.COLOR_BACKGROUND)
        try:
            icon_path = resource_path('app_icon.ico')
            self.iconbitmap(icon_path)
        except tk.TclError:
            logging.warning("Ficheiro 'app_icon.ico' não encontrado.")

        self.df_files, self.df_folders = pd.DataFrame(), pd.DataFrame()
        self.duplicate_groups, self.old_files, self.big_files, self.storage_summary = [], [], [], {}
        self.current_path = tk.StringVar(value=_("select_folder_prompt"))
        self.filter_text_var, self.filter_min_size_var, self.filter_max_size_var = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.filter_unit_var = tk.StringVar(value="MB")
        self.category_vars = {}
        self.category_map = {
            _("category_images"): ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg'],
            _("category_music"): ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.wma', '.m4a'],
            _("category_videos"): ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'],
            _("category_documents"): ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.rtf', '.csv'],
            _("category_compressed"): ['.zip', '.rar', '.7z', '.tar', '.gz', '.iso', '.jar'],
            _("category_system"): ['.exe', '.dll', '.sys', '.ini', '.drv', '.bat', '.sh']
        }
        self.create_menubar()
        self.create_interface()
        self.setup_styles()
        self.tree.bind('<<TreeviewOpen>>', self.on_tree_open)
        self.tree.bind('<<TreeviewSelect>>', self.on_folder_select)
        self.populate_root_nodes()
        self.create_context_menu()
        logging.info("Aplicação iniciada com sucesso.")
        splash.destroy()
        self.deiconify()

    def load_theme_colors(self):
        colors = themes.get_theme_colors()
        self.COLOR_BACKGROUND, self.COLOR_CONTENT_BG, self.COLOR_TEXT = colors["BACKGROUND"], colors["CONTENT_BG"], colors["TEXT"]
        self.COLOR_ACCENT, self.COLOR_SUCCESS, self.COLOR_TREE_HEADING_BG = colors["ACCENT"], colors["SUCCESS"], colors["TREE_HEADING_BG"]
        self.FONT_DEFAULT, self.FONT_LABEL = ("Segoe UI", 10), ("Segoe UI", 11, "bold")

    def create_menubar(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        preferences_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=_("preferences"), menu=preferences_menu)
        theme_menu = tk.Menu(preferences_menu, tearoff=0)
        preferences_menu.add_cascade(label=_("theme"), menu=theme_menu)
        theme_menu.add_command(label=_("light_theme"), command=lambda: self.apply_theme("light"))
        theme_menu.add_command(label=_("dark_theme"), command=lambda: self.apply_theme("dark"))
        lang_menu = tk.Menu(preferences_menu, tearoff=0)
        preferences_menu.add_cascade(label=_("language"), menu=lang_menu)
        lang_menu.add_command(label="Português (PT)", command=lambda: self.change_language("pt_PT"))
        lang_menu.add_command(label="English (US)", command=lambda: self.change_language("en_US"))
        lang_menu.add_command(label="Español (AR)", command=lambda: self.change_language("es_AR"))

    def apply_theme(self, theme_name: str):
        themes.save_theme_setting(theme_name)
        self.load_theme_colors()
        self.configure(background=self.COLOR_BACKGROUND)
        for frame in [self.main_frame, self.nav_frame, self.view_frame]:
            if frame.winfo_exists(): frame.configure(style='TFrame')
        self.setup_styles()
        if self.fig_canvas: self.update_pie_chart()

    def change_language(self, language_code: str):
        i18n.save_language_setting(language_code)
        messagebox.showinfo(title=_("lang_changed_title"), message=_("lang_changed_message"))

    def setup_styles(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', background=self.COLOR_BACKGROUND, foreground=self.COLOR_TEXT, fieldbackground=self.COLOR_CONTENT_BG, font=self.FONT_DEFAULT)
        style.map('.', background=[('active', self.COLOR_ACCENT)], foreground=[('active', self.COLOR_TEXT)])
        style.configure('TFrame', background=self.COLOR_BACKGROUND)
        style.configure('TLabel', background=self.COLOR_BACKGROUND, foreground=self.COLOR_TEXT)
        style.configure('TLabelframe', background=self.COLOR_BACKGROUND, bordercolor=self.COLOR_TEXT, relief=tk.SOLID)
        style.configure('TLabelframe.Label', background=self.COLOR_BACKGROUND, foreground=self.COLOR_TEXT, font=self.FONT_LABEL)
        style.configure('TButton', background=self.COLOR_CONTENT_BG, foreground=self.COLOR_TEXT, font=self.FONT_DEFAULT, padding=5)
        style.map('TButton', background=[('active', self.COLOR_ACCENT)])
        style.configure('Accent.TButton', background=self.COLOR_ACCENT, font=('Segoe UI', 10, 'bold'))
        style.map('Accent.TButton', background=[('active', self.COLOR_SUCCESS)])
        style.configure('Treeview', rowheight=25, fieldbackground=self.COLOR_CONTENT_BG, background=self.COLOR_CONTENT_BG, foreground=self.COLOR_TEXT)
        style.map('Treeview', background=[('selected', self.COLOR_ACCENT)])
        style.configure('Treeview.Heading', background=self.COLOR_TREE_HEADING_BG, foreground=self.COLOR_TEXT, font=('Segoe UI', 10, 'bold'), padding=5)
        style.configure('TNotebook', background=self.COLOR_BACKGROUND)
        style.configure('TNotebook.Tab', background=self.COLOR_CONTENT_BG, foreground=self.COLOR_TEXT, padding=[10, 5])
        style.map('TNotebook.Tab', background=[('selected', self.COLOR_ACCENT)], foreground=[('selected', self.COLOR_TEXT)])
        style.configure('custom.Horizontal.TProgressbar', troughcolor=self.COLOR_CONTENT_BG, background=self.COLOR_ACCENT)

    def create_interface(self):
        self.main_frame = ttk.Frame(self, padding=10)
        self.main_frame.pack(fill='both', expand=True)
        self.paned_window = ttk.PanedWindow(self.main_frame, orient='horizontal')
        self.paned_window.pack(fill='both', expand=True)
        self.nav_frame = ttk.LabelFrame(self.paned_window, text=_("nav_header"), padding=5)
        self.paned_window.add(self.nav_frame, weight=1)
        self.tree = ttk.Treeview(self.nav_frame, show="tree headings")
        self.tree.heading("#0", text=_("nav_header_col"))
        tree_scrollbar = ttk.Scrollbar(self.nav_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        tree_scrollbar.pack(side='right', fill='y')
        self.tree.pack(fill='both', expand=True)
        self.view_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.view_frame, weight=3)
        self.create_view_panel()
        
    def create_view_panel(self):
        # Frame para a linha de cima (Caminho da pasta e botão de iniciar)
        top_action_frame = ttk.Frame(self.view_frame)
        top_action_frame.pack(fill='x', pady=5)
        
        ttk.Label(top_action_frame, text=_("current_folder"), font=self.FONT_LABEL).pack(side='left', padx=(0, 5))
        path_label = ttk.Label(top_action_frame, textvariable=self.current_path, font=('Segoe UI', 10, 'italic'), relief='sunken', padding=5)
        path_label.pack(side='left', fill='x', expand=True)
        
        self.btn_start_scan = ttk.Button(top_action_frame, text=_("start_scan"), command=self.start_initial_scan, state='disabled', style='Accent.TButton')
        self.btn_start_scan.pack(side='left', padx=5)

        # Frame separado para os outros botões de análise
        analysis_btns_frame = ttk.Frame(self.view_frame)
        analysis_btns_frame.pack(fill='x', pady=(0, 5), padx=20)
        
        self.btn_find_duplicates = ttk.Button(analysis_btns_frame, text=_("find_duplicates"), command=self.start_duplicate_search, state='disabled')
        self.btn_find_duplicates.pack(side='left', padx=(0,5))
        self.btn_find_old_files = ttk.Button(analysis_btns_frame, text=_("find_old_files"), command=self.start_old_files_search, state='disabled')
        self.btn_find_old_files.pack(side='left', padx=5)
        self.btn_find_big_files = ttk.Button(analysis_btns_frame, text=_("find_big_files"), command=self.start_big_files_search, state='disabled')
        self.btn_find_big_files.pack(side='left', padx=5)

        # Cria o Notebook (as abas)
        self.notebook = ttk.Notebook(self.view_frame)
        self.notebook.pack(fill='both', expand=True, pady=5)
        
        # Adiciona as abas ao Notebook
        self.summary_tab, self.chart_tab, self.files_tab, self.duplicates_tab, self.old_files_tab, self.big_files_tab = (ttk.Frame(self.notebook) for i in range(6))
        self.notebook.add(self.summary_tab, text=_("summary_tab"))
        self.notebook.add(self.chart_tab, text=_("chart_tab"))
        self.notebook.add(self.files_tab, text=_("list_tab"))
        self.notebook.add(self.duplicates_tab, text=_("duplicates_tab"))
        self.notebook.add(self.old_files_tab, text=_("old_files_tab"))
        self.notebook.add(self.big_files_tab, text=_("big_files_tab"))
        
        # Cria os rótulos de estado e outros widgets
        self.status_labels = {
            "chart": ttk.Label(self.chart_tab, text=_("select_folder_prompt"), font=('Segoe UI', 14)),
            "duplicates": ttk.Label(self.duplicates_tab, text=""), "old_files": ttk.Label(self.old_files_tab, text=""),
            "big_files": ttk.Label(self.big_files_tab, text="")
        }
        self.status_labels["chart"].pack(pady=50)

        self.fig_canvas = None
        self.progress_bar = ttk.Progressbar(self.view_frame, orient='horizontal', mode='indeterminate', style='custom.Horizontal.TProgressbar')
        
        # Cria o conteúdo de cada aba
        self.create_summary_view(self.summary_tab)
        self.create_filter_panel(self.files_tab)
        self.create_file_list_table(self.files_tab)
        self.create_duplicates_table(self.duplicates_tab)
        self.create_old_files_table(self.old_files_tab)
        self.create_big_files_table(self.big_files_tab)
    def create_summary_view(self, parent_tab):
        frame = ttk.Frame(parent_tab, padding=20)
        frame.pack(fill='both', expand=True)
        self.lbl_total_files, self.lbl_total_size, self.lbl_avg_size = (ttk.Label(frame, text="", font=self.FONT_LABEL) for i in range(3))
        self.lbl_total_files.pack(anchor='w', pady=5); self.lbl_total_size.pack(anchor='w', pady=5); self.lbl_avg_size.pack(anchor='w', pady=5)
        export_button = ttk.Button(frame, text=_("export_pdf"), command=self.export_to_pdf, state='disabled')
        export_button.pack(anchor='w', pady=20)
        self.btn_export = export_button

    def create_filter_panel(self, parent_tab):
        filter_frame = ttk.LabelFrame(parent_tab, text=_("filters"), padding=10)
        filter_frame.pack(fill='x', padx=5, pady=5)
        filter_frame.columnconfigure(1, weight=1)
        left_frame, right_frame = ttk.Frame(filter_frame), ttk.Frame(filter_frame)
        left_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 10)); right_frame.grid(row=0, column=1, sticky='nsew')
        ttk.Label(left_frame, text=_("filter_name_path")).pack(anchor='w'); ttk.Entry(left_frame, textvariable=self.filter_text_var).pack(anchor='w', fill='x')
        size_frame = ttk.Frame(left_frame); size_frame.pack(anchor='w', pady=(10,0))
        ttk.Label(size_frame, text=_("filter_size")).pack(side='left'); ttk.Entry(size_frame, textvariable=self.filter_min_size_var, width=8).pack(side='left')
        ttk.Label(size_frame, text="<").pack(side='left', padx=(5,0)); ttk.Entry(size_frame, textvariable=self.filter_max_size_var, width=8).pack(side='left')
        ttk.Combobox(size_frame, textvariable=self.filter_unit_var, values=["KB", "MB", "GB"], width=4, state="readonly").pack(side='left', padx=5)
        ttk.Label(right_frame, text=_("filter_categories")).pack(anchor='w')
        types_frame = ttk.Frame(right_frame); types_frame.pack(anchor='w', pady=5)
        col, row = 0, 0
        for category_text in self.category_map.keys():
            var = tk.BooleanVar(); cb = ttk.Checkbutton(types_frame, text=category_text, variable=var); cb.grid(row=row, column=col, sticky='w', padx=5)
            self.category_vars[category_text] = var; col = (col + 1) % 3
            if col == 0: row += 1
        action_frame = ttk.Frame(left_frame); action_frame.pack(anchor='w', pady=(15,0))
        self.btn_apply_filters = ttk.Button(action_frame, text=_("apply_filters"), command=self.apply_filters); self.btn_apply_filters.pack(side='left')
        self.btn_clear_filters = ttk.Button(action_frame, text=_("clear_filters"), command=self.clear_filters); self.btn_clear_filters.pack(side='left', padx=5)
        
    def create_file_list_table(self, parent_tab):
        frame = ttk.Frame(parent_tab); frame.pack(fill='both', expand=True, padx=5, pady=5)
        cols = (_("col_name"), _("col_size_mb"), _("col_mdate"), _("col_fullpath")); self.files_tree = ttk.Treeview(frame, columns=cols, show='headings')
        for col in cols: self.files_tree.heading(col, text=col, command=lambda _col=col: self.sort_treeview_column(self.files_tree, _col, False))
        self.files_tree.column(_("col_name"), width=250); self.files_tree.column(_("col_size_mb"), anchor='e', width=120)
        self.files_tree.column(_("col_mdate"), width=150); self.files_tree.column(_("col_fullpath"), width=400)
        v_scroll, h_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.files_tree.yview), ttk.Scrollbar(frame, orient="horizontal", command=self.files_tree.xview)
        self.files_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.pack(side='right', fill='y'); h_scroll.pack(side='bottom', fill='x'); self.files_tree.pack(fill='both', expand=True)
        self.files_tree.bind("<Double-1>", self.on_double_click_item)

    def on_double_click_item(self, event): self.open_file_location()

    def create_duplicates_table(self, parent_tab):
        frame = ttk.Frame(parent_tab); frame.pack(fill='both', expand=True, padx=5, pady=5)
        cols = (_("col_file_group"), _("col_size_mb")); self.duplicates_tree = ttk.Treeview(frame, columns=cols, show='headings')
        for col in cols: self.duplicates_tree.heading(col, text=col)
        self.duplicates_tree.column(_("col_file_group"), width=600); self.duplicates_tree.column(_("col_size_mb"), anchor='e', width=120)
        v_scroll, h_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.duplicates_tree.yview), ttk.Scrollbar(frame, orient="horizontal", command=self.duplicates_tree.xview)
        self.duplicates_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.pack(side='right', fill='y'); h_scroll.pack(side='bottom', fill='x'); self.duplicates_tree.pack(fill='both', expand=True)
        btn_frame = ttk.Frame(parent_tab); btn_frame.pack(fill='x', padx=5)
        self.btn_delete_duplicates = ttk.Button(btn_frame, text=_("delete_selected"), command=self.delete_selected_duplicates, state='disabled'); self.btn_delete_duplicates.pack(side='left', pady=5)
        
    def create_old_files_table(self, parent_tab):
        frame = ttk.Frame(parent_tab); frame.pack(fill='both', expand=True, padx=5, pady=5)
        cols = (_("col_name"), _("col_size_mb"), _("col_last_access")); self.old_files_tree = ttk.Treeview(frame, columns=cols, show='headings')
        for col in cols: self.old_files_tree.heading(col, text=col)
        self.old_files_tree.column(_("col_name"), width=500); self.old_files_tree.column(_("col_size_mb"), anchor='e', width=120)
        self.old_files_tree.column(_("col_last_access"), anchor='center', width=150)
        v_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.old_files_tree.yview); v_scroll.pack(side='right', fill='y')
        self.old_files_tree.configure(yscrollcommand=v_scroll.set); self.old_files_tree.pack(fill='both', expand=True)
        btn_frame = ttk.Frame(parent_tab); btn_frame.pack(fill='x', padx=5)
        self.btn_compress_old_files = ttk.Button(btn_frame, text=_("compress_selected"), command=self.compress_selected_old_files, state='disabled'); self.btn_compress_old_files.pack(side='left', pady=5)

    def create_big_files_table(self, parent_tab):
        frame = ttk.Frame(parent_tab); frame.pack(fill='both', expand=True, padx=5, pady=5)
        cols = (_("col_name"), _("col_size_mb"), _("col_mdate"), _("col_fullpath")); self.big_files_tree = ttk.Treeview(frame, columns=cols, show='headings')
        for col in cols: self.big_files_tree.heading(col, text=col, command=lambda _col=col: self.sort_treeview_column(self.big_files_tree, _col, False))
        self.big_files_tree.column(_("col_name"), width=250); self.big_files_tree.column(_("col_size_mb"), anchor='e', width=120)
        self.big_files_tree.column(_("col_mdate"), width=150); self.big_files_tree.column(_("col_fullpath"), width=400)
        v_scroll, h_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.big_files_tree.yview), ttk.Scrollbar(frame, orient="horizontal", command=self.big_files_tree.xview)
        self.big_files_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.pack(side='right', fill='y'); h_scroll.pack(side='bottom', fill='x'); self.big_files_tree.pack(fill='both', expand=True)
        
    def create_context_menu(self):
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label=_("open_location"), command=self.open_file_location); self.context_menu.add_separator()
        self.context_menu.add_command(label=_("open_file"), command=self.open_file)
        for tree in [self.files_tree, self.big_files_tree, self.duplicates_tree, self.old_files_tree]:
            tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Button-3>", self.show_nav_context_menu)

    def show_context_menu(self, event):
        tree = event.widget; item_id = tree.identify_row(event.y)
        if item_id:
            tree.selection_set(item_id)
            try:
                item_path = tree.item(item_id)['values'][3]
                self.context_menu.entryconfig(_("open_file"), state="normal" if os.path.isfile(item_path) else "disabled")
            except IndexError:
                item_path = tree.item(item_id)['values'][0]
                if "Grupo" in item_path: self.context_menu.entryconfig(_("open_file"), state="disabled")
            self.context_menu.post(event.x_root, event.y_root)

    def show_nav_context_menu(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self.tree.selection_set(item_id); self.context_menu.entryconfig(_("open_file"), state="disabled")
            self.context_menu.entryconfig(_("open_location"), label=_("open_folder")); self.context_menu.post(event.x_root, event.y_root)

    def open_file_location(self):
        try:
            tree = self.focus_get()
            if not isinstance(tree, ttk.Treeview) or not tree.selection(): return
            item_id = tree.selection()[0]; values = tree.item(item_id)['values']
            item_path = values[0] if tree is self.tree else values[3] if len(values) > 3 else values[0].strip().replace("└─ ", "")
            folder_path = os.path.dirname(item_path) if os.path.isfile(item_path) else item_path
            if sys.platform == "win32": os.startfile(folder_path)
            elif sys.platform == "darwin": subprocess.run(["open", folder_path])
            else: subprocess.run(["xdg-open", folder_path])
        except Exception as e: messagebox.showerror(_("error_open_folder"), f"{_('error_open_folder')}\n{e}")

    def open_file(self):
        try:
            tree = self.focus_get()
            if not isinstance(tree, ttk.Treeview) or not tree.selection(): return
            item_id = tree.selection()[0]; values = tree.item(item_id)['values']
            file_path = values[3] if len(values) > 3 else values[0].strip().replace("└─ ", "")
            if os.path.isfile(file_path):
                if sys.platform == "win32": os.startfile(file_path)
                elif sys.platform == "darwin": subprocess.run(["open", file_path])
                else: subprocess.run(["xdg-open", file_path])
        except Exception as e: messagebox.showerror(_("error_open_file"), f"{_('error_open_file')}\n{e}")
    
    def populate_root_nodes(self):
        if sys.platform == "win32":
            import string
            drives = [f'{d}:\\' for d in string.ascii_uppercase if os.path.exists(f'{d}:')]
            for drive in drives:
                node = self.tree.insert('', 'end', text=drive, values=[drive, 'drive']); self.tree.insert(node, 'end')
        else:
            root_node = self.tree.insert('', 'end', text="/", values=["/", 'folder']); self.tree.insert(root_node, 'end')

    def on_tree_open(self, event):
        parent_id = self.tree.focus();
        if not parent_id: return
        parent_path = self.tree.item(parent_id)['values'][0]
        self.tree.delete(*self.tree.get_children(parent_id))
        try:
            for item in os.listdir(parent_path):
                full_path = os.path.join(parent_path, item)
                if os.path.isdir(full_path):
                    try:
                        os.listdir(full_path); node = self.tree.insert(parent_id, 'end', text=item, values=[full_path, 'folder'])
                        self.tree.insert(node, 'end') 
                    except (PermissionError, OSError): continue
        except (PermissionError, OSError) as e:
            logging.warning(f"Não foi possível abrir o diretório {parent_path}: {e}")

    def reset_view_state(self):
        if self.fig_canvas: self.fig_canvas.get_tk_widget().destroy()
        self.status_labels['chart'].config(text=_("select_folder_prompt")); self.status_labels['chart'].pack(pady=50)
        self.clear_filters()
        for tree in [self.files_tree, self.duplicates_tree, self.old_files_tree, self.big_files_tree]:
            if hasattr(self, 'tree') and self.tree.winfo_exists(): tree.delete(*tree.get_children())
        for btn in [self.btn_find_duplicates, self.btn_find_old_files, self.btn_find_big_files, self.btn_delete_duplicates, self.btn_compress_old_files, self.btn_export]:
             if btn.winfo_exists(): btn.config(state='disabled')

    def apply_filters(self):
        unit = self.filter_unit_var.get(); multiplier = {"KB": 1024, "MB": 1024**2, "GB": 1024**3}[unit]
        try: min_size, max_size = float(self.filter_min_size_var.get() or 0) * multiplier, float(self.filter_max_size_var.get() or float('inf')) * multiplier
        except ValueError: messagebox.showerror(_("error_value_title"), _("error_value_message")); return
        texto = self.filter_text_var.get().lower()
        exts = [ext for cat, var in self.category_vars.items() if var.get() for ext in self.category_map[cat]]
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

    def sort_treeview_column(self, tv, col, reverse):
        try: l = [(float(tv.set(k, col).replace(",", "")), k) for k in tv.get_children('')]
        except (ValueError, tk.TclError): l = [(tv.set(k, col), k) for k in tv.get_children('')]
        l.sort(key=lambda item: item[0], reverse=reverse)
        for index, (val, k) in enumerate(l): tv.move(k, '', index)
        tv.heading(col, command=lambda _col=col: self.sort_treeview_column(tv, _col, not reverse))
        
    def populate_file_list_table(self, dataframe):
        self.files_tree.delete(*self.files_tree.get_children())
        for _, row in dataframe.iterrows():
            name, size_gb, mtime, path = row['name'], row['size'] / (1024**3), datetime.fromtimestamp(row['mtime']).strftime('%Y-%m-%d %H:%M'), row['path']
            self.files_tree.insert("", "end", values=(name, f"{size_gb:,.4f}", mtime, path))

    def populate_duplicates_table(self):
        self.duplicates_tree.delete(*self.duplicates_tree.get_children())
        for i, group in enumerate(self.duplicate_groups):
            if not group: continue
            size_mb, group_title = os.path.getsize(group[0]) / (1024*1024), _("group_files").format(group_num=i + 1, count=len(group))
            parent = self.duplicates_tree.insert("", "end", iid=f"G{i}", values=(group_title, f"{size_mb:,.2f}"))
            for file_path in group: self.duplicates_tree.insert(parent, "end", values=(f"  └─ {file_path}", ""))

    def populate_old_files_table(self):
        self.old_files_tree.delete(*self.old_files_tree.get_children())
        self.old_files.sort(key=lambda x: x['atime'])
        for item in self.old_files:
            size_gb, atime_str = item['size'] / (1024**3), datetime.fromtimestamp(item['atime']).strftime('%Y-%m-%d')
            self.old_files_tree.insert("", "end", values=(item['path'], f"{size_gb:,.4f}", atime_str), iid=item['path'])

    def populate_big_files_table(self):
        self.big_files_tree.delete(*self.big_files_tree.get_children())
        for item in self.big_files:
            name, size_gb, mtime, path = os.path.basename(item['path']), item['size'] / (1024**3), datetime.fromtimestamp(item['mtime']).strftime('%Y-%m-%d %H:%M'), item['path']
            self.big_files_tree.insert("", "end", values=(name, f"{size_gb:,.4f}", mtime, path))

    def delete_selected_duplicates(self):
        selected_items = self.duplicates_tree.selection()
        files_to_delete = [self.duplicates_tree.item(item)['values'][0].strip().replace("└─ ", "") for item in selected_items if self.duplicates_tree.parent(item)]
        if not files_to_delete: messagebox.showwarning(_("delete_warning_title"), _("delete_warning_message")); return
        confirm_msg = _("delete_confirm_message").format(count=len(files_to_delete))
        if messagebox.askyesno(_("delete_confirm_title"), confirm_msg):
            deleted_count = 0
            for file in files_to_delete:
                try: os.remove(file); deleted_count +=1
                except Exception as e: logging.error(f"Falha ao apagar ficheiro duplicado {file}", exc_info=True)
            messagebox.showinfo(_("delete_done_title"), _("delete_done_message").format(count=deleted_count)); self.start_duplicate_search()

    def export_to_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if not path: return
        try:
            with pd.ExcelWriter(path) as writer:
                all_content = pd.concat([self.df_folders, self.df_files], ignore_index=True)
                if not all_content.empty: all_content.to_excel(writer, sheet_name=_("list_tab"), index=False)
                if self.duplicate_groups: pd.DataFrame(self.duplicate_groups).to_excel(writer, sheet_name=_("duplicates_tab"), index=False)
                if self.old_files: pd.DataFrame(self.old_files).to_excel(writer, sheet_name=_("old_files_tab"), index=False)
            logging.info(f"Resultados exportados com sucesso para {path}")
            messagebox.showinfo(_("export_success_title"), _("export_success_message").format(path=path))
        except Exception as e:
            logging.error(f"Erro ao exportar para Excel em {path}", exc_info=True)
            messagebox.showerror(_("export_error_title"), _("export_error_message"))

    def compress_selected_old_files(self):
        selected_iids = self.old_files_tree.selection()
        if not selected_iids: messagebox.showwarning(_("compress_no_selection_title"), _("compress_no_selection_message")); return
        confirm_msg = _("compress_confirm_message").format(count=len(selected_iids))
        if not messagebox.askyesno(_("compress_confirm_title"), confirm_msg): return
        files_to_compress = [self.old_files_tree.item(iid)['values'][0] for iid in selected_iids]
        save_path = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("ZIP archive", "*.zip")])
        if not save_path: return
        self.threaded_task(analysis.run_compression_and_deletion, files_to_compress, save_path)

    def export_to_pdf(self):
        if self.df_files.empty and self.df_folders.empty: messagebox.showwarning(_("delete_warning_title"), "Não há dados para exportar."); return
        save_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Document", "*.pdf")])
        if not save_path: return
        chart_path = resource_path("temp_chart.png")
        try:
            if self.fig_canvas: self.fig_canvas.figure.savefig(chart_path, facecolor=self.COLOR_BACKGROUND, bbox_inches='tight')
            all_content = pd.concat([self.df_folders, self.df_files], ignore_index=True)
            utils.export_report_pdf(all_content, chart_path, save_path, self.storage_summary)
            messagebox.showinfo(_("export_success_title"), _("export_success_message").format(path=save_path))
        except Exception as e:
            logging.error(f"Erro ao exportar PDF: {e}", exc_info=True)
            messagebox.showerror(_("export_error_title"), _("export_error_message"))
        finally:
            if os.path.exists(chart_path): os.remove(chart_path)

    def get_status_label(self):
        try:
            current_tab_widget = self.notebook.select()
            tab_map = { str(self.duplicates_tab): self.status_labels["duplicates"], str(self.old_files_tab): self.status_labels["old_files"], str(self.big_files_tab): self.status_labels["big_files"] }
            return tab_map.get(current_tab_widget, self.status_labels["chart"])
        except (tk.TclError, AttributeError): return self.status_labels.get("chart", ttk.Label(self))

    def set_determinate_progress(self, max_value): self.progress_bar.config(mode='determinate' if max_value > 0 else 'indeterminate', maximum=max_value, value=0)
    def update_progress_value(self, value): self.progress_bar['value'] = value

    def set_ui_busy(self, is_busy: bool):
        self.config(cursor="watch" if is_busy else "")
        state = 'disabled' if is_busy else 'normal'
        if is_busy: self.tree.unbind("<<TreeviewSelect>>")
        else: self.tree.bind("<<TreeviewSelect>>", self.on_folder_select)
        buttons = [self.btn_find_duplicates, self.btn_find_old_files, self.btn_find_big_files, self.btn_delete_duplicates, self.btn_compress_old_files, self.btn_export, self.btn_start_scan]
        for btn in buttons:
            if btn.winfo_exists(): btn.config(state=state)
        if not is_busy and not os.path.isdir(self.current_path.get()):
             for btn in [self.btn_find_duplicates, self.btn_find_old_files, self.btn_find_big_files, self.btn_export, self.btn_start_scan]:
                 if btn.winfo_exists(): btn.config(state='disabled')
        self.update_idletasks()
        if is_busy:
            self.progress_bar.pack(fill='x', padx=10, pady=5, side='bottom')
            if self.progress_bar['mode'] == 'indeterminate': self.progress_bar.start(10)
        else:
            self.progress_bar.stop(); self.progress_bar.pack_forget()
        
    def threaded_task(self, func, *args):
        self.set_ui_busy(True); thread = threading.Thread(target=self.run_task_wrapper, args=(func, self, *args), daemon=True); thread.start()

    def run_task_wrapper(self, func, *args):
        try: func(*args)
        except Exception as e:
            logging.error(f"Erro na thread da função {func.__name__}", exc_info=True)
            self.after(0, lambda: messagebox.showerror(_("export_error_title"), _("export_error_message")))
        finally: self.after(0, self.set_ui_busy, False)

    def on_folder_select(self, event):
        """ ATUALIZADO: Agora apenas seleciona a pasta e ativa o botão de varredura. """
        if not self.tree.selection(): return
        folder_id = self.tree.selection()[0]
        folder_path = self.tree.item(folder_id)['values'][0]
        if not os.path.isdir(folder_path):
            self.current_path.set(_("select_folder_prompt"))
            self.btn_start_scan.config(state='disabled')
            return
        self.current_path.set(folder_path)
        self.reset_view_state()
        self.status_labels['chart'].config(text=_("folder_selected"))
        self.btn_start_scan.config(state='normal')

    def start_initial_scan(self):
        """ Inicia a análise GERAL quando o botão de varredura é clicado. """
        path = self.current_path.get()
        if not os.path.isdir(path): return
        self.status_labels['chart'].config(text=_("analyzing").format(folder=os.path.basename(path)))
        self.status_labels['chart'].pack(pady=50)
        analyses_to_run = {"duplicates": False, "old_files": False, "big_files": False}
        self.threaded_task(analysis.run_full_scan_and_analyze, path, analyses_to_run, {})

    def start_duplicate_search(self):
        path = self.current_path.get();
        if not os.path.isdir(path): return
        self.notebook.select(self.duplicates_tab)
        self.threaded_task(analysis.run_full_scan_and_analyze, path, {"duplicates": True}, {})

    def start_old_files_search(self):
        path = self.current_path.get();
        if not os.path.isdir(path): return
        days = simpledialog.askinteger(_("old_files_found_title"), _("old_files_prompt"), initialvalue=180, minvalue=1, parent=self)
        if not days: return
        self.notebook.select(self.old_files_tab)
        self.threaded_task(analysis.run_full_scan_and_analyze, path, {"old_files": True}, {"days_old": days})

    def start_big_files_search(self):
        path = self.current_path.get();
        if not os.path.isdir(path): return
        top_n = simpledialog.askinteger(_("big_files_tab"), _("big_files_prompt"), initialvalue=50, minvalue=10, parent=self)
        if not top_n: return
        self.notebook.select(self.big_files_tab)
        self.threaded_task(analysis.run_full_scan_and_analyze, path, {"big_files": True}, {"top_n": top_n})
        
    def update_quick_analysis_view(self):
        """ ATUALIZADO: Agora ativa todos os botões de análise secundária. """
        for btn in [self.btn_find_duplicates, self.btn_find_old_files, self.btn_find_big_files, self.btn_export]:
             if btn.winfo_exists(): btn.config(state='normal')
        
        all_content = pd.concat([self.df_folders, self.df_files], ignore_index=True)
        if all_content.empty: 
            self.status_labels['chart'].config(text=_("empty_folder"))
            self.set_ui_busy(False)
            return
        self.apply_filters()
        self.update_pie_chart()
        self.threaded_task(analysis.compute_storage_summary, pd.concat([self.df_folders, self.df_files], ignore_index=True))
        
    def update_pie_chart(self):
        if self.fig_canvas: self.fig_canvas.get_tk_widget().destroy()
        self.status_labels['chart'].pack_forget()
        chart_data = pd.concat([self.df_folders, self.df_files], ignore_index=True)
        if chart_data.empty: return
        top_n = 7; df_plot = chart_data.nlargest(top_n, 'size').copy()
        if len(chart_data) > top_n:
            outros_size = chart_data.nsmallest(len(chart_data) - top_n, 'size')['size'].sum()
            outros_row = pd.DataFrame([{'name': _("chart_others"), 'size': outros_size}])
            df_plot = pd.concat([df_plot, outros_row], ignore_index=True)
        total_size = chart_data['size'].sum();
        if total_size == 0: return
        labels = [f"{row['name']} ({row['size']/total_size:.1%})" for _, row in df_plot.iterrows()]
        plt.style.use('seaborn-v0_8-deep'); fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
        fig.patch.set_facecolor(self.COLOR_BACKGROUND); ax.set_facecolor(self.COLOR_BACKGROUND)
        fig.subplots_adjust(left=0.05, right=0.7)
        wedges, chart_texts = ax.pie(df_plot['size'], startangle=90, wedgeprops=dict(width=0.4, edgecolor=self.COLOR_BACKGROUND), radius=1.2)
        legend = ax.legend(wedges, labels, title=_("chart_legend_title"), loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), facecolor=self.COLOR_BACKGROUND, edgecolor=self.COLOR_BACKGROUND)
        for text in legend.get_texts(): text.set_color(self.COLOR_TEXT)
        legend.get_title().set_color(self.COLOR_TEXT)
        title_text = _("chart_title").format(folder=os.path.basename(self.current_path.get()))
        ax.set_title(title_text, pad=20, fontdict={'fontsize': 14, 'color': self.COLOR_TEXT})
        self.fig_canvas = FigureCanvasTkAgg(fig, master=self.chart_tab); self.fig_canvas.draw()
        self.fig_canvas.get_tk_widget().pack(fill='both', expand=True, padx=5, pady=5)

    def update_duplicates_view(self):
        self.get_status_label().config(text=""); self.populate_duplicates_table()
        if self.duplicate_groups:
            self.btn_delete_duplicates.config(state='normal')
            messagebox.showinfo(_("duplicates_found_title"), _("duplicates_found_message").format(count=len(self.duplicate_groups)))
        else: messagebox.showinfo(_("no_duplicates_title"), _("no_duplicates_message"))

    def update_old_files_view(self):
        self.get_status_label().config(text=""); self.populate_old_files_table()
        if self.old_files:
            self.btn_compress_old_files.config(state='normal')
            messagebox.showinfo(_("old_files_found_title"), _("old_files_found_message").format(count=len(self.old_files)))
        else: messagebox.showinfo(_("old_files_found_title"), _("no_old_files_found_message"))
    
    def update_big_files_view(self):
        self.get_status_label().config(text=""); self.populate_big_files_table()

    def update_storage_summary_view(self):
        summary = self.storage_summary
        self.lbl_total_files.config(text=f"{_('total_files')} {summary.get('total_files', 0)}")
        self.lbl_total_size.config(text=f"{_('total_size_gb')} {summary.get('total_size_gb', 0):.2f} GB")
        self.lbl_avg_size.config(text=f"{_('avg_size_mb')} {summary.get('avg_size_mb', 0):.2f} MB")
