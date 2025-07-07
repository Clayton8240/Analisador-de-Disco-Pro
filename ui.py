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

import analysis
import utils
import i18n
import themes

_ = i18n.get_text

class FinalDiskAnalyzerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.load_theme_colors()

        self.title(_("title"))
        self.geometry("1200x800")
        self.configure(background=self.COLOR_BACKGROUND)

        try:
            self.iconbitmap('app_icon.ico')
        except tk.TclError:
            logging.warning("Ficheiro 'app_icon.ico' não encontrado.")

        self.df_files = pd.DataFrame()
        self.df_folders = pd.DataFrame()
        self.duplicate_groups = []
        self.old_files = []
        self.big_files = []
        self.storage_summary = {}
        
        self.current_path = tk.StringVar(value=_("select_folder_prompt"))
        self.filter_text_var = tk.StringVar()
        self.filter_min_size_var = tk.StringVar()
        self.filter_max_size_var = tk.StringVar()
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

    def load_theme_colors(self):
        colors = themes.get_theme_colors()
        self.COLOR_BACKGROUND = colors["BACKGROUND"]
        self.COLOR_CONTENT_BG = colors["CONTENT_BG"]
        self.COLOR_TEXT = colors["TEXT"]
        self.COLOR_ACCENT = colors["ACCENT"]
        self.COLOR_SUCCESS = colors["SUCCESS"]
        self.COLOR_TREE_HEADING_BG = colors["TREE_HEADING_BG"]
        self.FONT_DEFAULT = ("Segoe UI", 10)
        self.FONT_LABEL = ("Segoe UI", 11, "bold")

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
        self.main_frame.configure(style='TFrame')
        self.nav_frame.configure(style='TLabelframe')
        self.view_frame.configure(style='TFrame')
        
        self.setup_styles()
        
        if self.fig_canvas:
            self.update_pie_chart()

    def change_language(self, language_code: str):
        i18n.save_language_setting(language_code)
        messagebox.showinfo(
            title=_("lang_changed_title"),
            message=_("lang_changed_message")
        )

    def setup_styles(self):
        style = ttk.Style(self)
        style.theme_use('clam')

        style.configure('.', background=self.COLOR_BACKGROUND, foreground=self.COLOR_TEXT, 
                        fieldbackground=self.COLOR_CONTENT_BG, font=self.FONT_DEFAULT)
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
        action_frame = ttk.Frame(self.view_frame)
        action_frame.pack(fill='x', pady=5)
        ttk.Label(action_frame, text=_("current_folder"), font=self.FONT_LABEL).pack(side='left')
        path_label = ttk.Label(action_frame, textvariable=self.current_path, font=('Segoe UI', 10, 'italic'), relief='sunken', padding=5)
        path_label.pack(side='left', fill='x', expand=True, padx=10)
        
        self.btn_find_duplicates = ttk.Button(action_frame, text=_("find_duplicates"), command=self.start_duplicate_search, state='disabled')
        self.btn_find_duplicates.pack(side='left', padx=(0,5))
        self.btn_find_old_files = ttk.Button(action_frame, text=_("find_old_files"), command=self.start_old_files_search, state='disabled')
        self.btn_find_old_files.pack(side='left')
        self.btn_find_big_files = ttk.Button(action_frame, text=_("find_big_files"), command=self.start_big_files_search, state='disabled')
        self.btn_find_big_files.pack(side='left', padx=5)

        self.notebook = ttk.Notebook(self.view_frame)
        self.notebook.pack(fill='both', expand=True, pady=5)
        
        self.summary_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.summary_tab, text=_("summary_tab"))
        self.chart_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.chart_tab, text=_("chart_tab"))
        self.files_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.files_tab, text=_("list_tab"))
        self.duplicates_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.duplicates_tab, text=_("duplicates_tab"))
        self.old_files_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.old_files_tab, text=_("old_files_tab"))
        self.big_files_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.big_files_tab, text=_("big_files_tab"))

        self.lbl_status = ttk.Label(self.chart_tab, text=_("select_folder_prompt"), font=('Segoe UI', 14))
        self.lbl_status.pack(pady=50)
        self.fig_canvas = None
        
        self.progress_bar = ttk.Progressbar(self.view_frame, orient='horizontal', mode='indeterminate', style='custom.Horizontal.TProgressbar')

        self.create_summary_view(self.summary_tab)
        self.create_filter_panel(self.files_tab)
        self.create_file_list_table(self.files_tab)
        self.create_duplicates_table(self.duplicates_tab)
        self.create_old_files_table(self.old_files_tab)
        self.create_big_files_table(self.big_files_tab)

    def create_summary_view(self, parent_tab):
        frame = ttk.Frame(parent_tab, padding=20)
        frame.pack(fill='both', expand=True)

        self.lbl_total_files = ttk.Label(frame, text="", font=self.FONT_LABEL)
        self.lbl_total_files.pack(anchor='w', pady=5)

        self.lbl_total_size = ttk.Label(frame, text="", font=self.FONT_LABEL)
        self.lbl_total_size.pack(anchor='w', pady=5)

        self.lbl_avg_size = ttk.Label(frame, text="", font=self.FONT_LABEL)
        self.lbl_avg_size.pack(anchor='w', pady=5)

        export_button = ttk.Button(frame, text=_("export_pdf"), command=self.export_to_pdf)
        export_button.pack(anchor='w', pady=20)

    def create_filter_panel(self, parent_tab):
        filter_frame = ttk.LabelFrame(parent_tab, text=_("filters"), padding=10)
        filter_frame.pack(fill='x', padx=5, pady=5)
        filter_frame.columnconfigure(1, weight=1)

        left_frame = ttk.Frame(filter_frame)
        left_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        
        ttk.Label(left_frame, text=_("filter_name_path")).pack(anchor='w')
        ttk.Entry(left_frame, textvariable=self.filter_text_var).pack(anchor='w', fill='x')
        
        size_frame = ttk.Frame(left_frame)
        size_frame.pack(anchor='w', pady=(10,0))
        ttk.Label(size_frame, text=_("filter_size")).pack(side='left')
        ttk.Entry(size_frame, textvariable=self.filter_min_size_var, width=8).pack(side='left')
        ttk.Label(size_frame, text="<").pack(side='left', padx=(5,0))
        ttk.Entry(size_frame, textvariable=self.filter_max_size_var, width=8).pack(side='left')
        ttk.Combobox(size_frame, textvariable=self.filter_unit_var, values=["KB", "MB", "GB"], width=4, state="readonly").pack(side='left', padx=5)

        right_frame = ttk.Frame(filter_frame)
        right_frame.grid(row=0, column=1, sticky='nsew')
        
        ttk.Label(right_frame, text=_("filter_categories")).pack(anchor='w')
        types_frame = ttk.Frame(right_frame)
        types_frame.pack(anchor='w', pady=5)
        
        col, row = 0, 0
        for category_text in self.category_map.keys():
            var = tk.BooleanVar()
            cb = ttk.Checkbutton(types_frame, text=category_text, variable=var)
            cb.grid(row=row, column=col, sticky='w', padx=5)
            self.category_vars[category_text] = var
            col += 1
            if col > 2:
                col = 0
                row += 1

        action_frame = ttk.Frame(left_frame)
        action_frame.pack(anchor='w', pady=(15,0))
        self.btn_apply_filters = ttk.Button(action_frame, text=_("apply_filters"), command=self.apply_filters)
        self.btn_apply_filters.pack(side='left')
        self.btn_clear_filters = ttk.Button(action_frame, text=_("clear_filters"), command=self.clear_filters)
        self.btn_clear_filters.pack(side='left', padx=5)
        
    def create_file_list_table(self, parent_tab):
        frame = ttk.Frame(parent_tab)
        frame.pack(fill='both', expand=True, padx=5, pady=5)
        cols = (_("col_name"), _("col_size_mb"), _("col_mdate"), _("col_fullpath"))
        self.files_tree = ttk.Treeview(frame, columns=cols, show='headings')
        for col in cols:
            self.files_tree.heading(col, text=col)
        self.files_tree.column(_("col_name"), width=250)
        self.files_tree.column(_("col_size_mb"), anchor='e', width=120)
        self.files_tree.column(_("col_mdate"), width=150)
        self.files_tree.column(_("col_fullpath"), width=400)
        v_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.files_tree.yview)
        h_scroll = ttk.Scrollbar(frame, orient="horizontal", command=self.files_tree.xview)
        self.files_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.pack(side='right', fill='y')
        h_scroll.pack(side='bottom', fill='x')
        self.files_tree.pack(fill='both', expand=True)
        self.files_tree.bind("<Double-1>", self.on_double_click_item)

    def on_double_click_item(self, event):
        self.open_file_location()

    def create_duplicates_table(self, parent_tab):
        frame = ttk.Frame(parent_tab)
        frame.pack(fill='both', expand=True, padx=5, pady=5)
        cols = (_("col_file_group"), _("col_size_mb"))
        self.duplicates_tree = ttk.Treeview(frame, columns=cols, show='headings')
        for col in cols:
            self.duplicates_tree.heading(col, text=col)
        self.duplicates_tree.column(_("col_file_group"), width=600)
        self.duplicates_tree.column(_("col_size_mb"), anchor='e', width=120)
        v_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.duplicates_tree.yview)
        h_scroll = ttk.Scrollbar(frame, orient="horizontal", command=self.duplicates_tree.xview)
        self.duplicates_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.pack(side='right', fill='y')
        h_scroll.pack(side='bottom', fill='x')
        self.duplicates_tree.pack(fill='both', expand=True)
        btn_frame = ttk.Frame(parent_tab)
        btn_frame.pack(fill='x', padx=5)
        self.btn_delete_duplicates = ttk.Button(btn_frame, text=_("delete_selected"), command=self.delete_selected_duplicates, state='disabled')
        self.btn_delete_duplicates.pack(side='left', pady=5)
        self.btn_export = ttk.Button(btn_frame, text=_("export_results"), command=self.export_to_excel, state='disabled')
        self.btn_export.pack(side='right', pady=5)
        
    def create_old_files_table(self, parent_tab):
        frame = ttk.Frame(parent_tab)
        frame.pack(fill='both', expand=True, padx=5, pady=5)
        cols = (_("col_name"), _("col_size_mb"), _("col_last_access"))
        self.old_files_tree = ttk.Treeview(frame, columns=cols, show='headings')
        for col in cols:
            self.old_files_tree.heading(col, text=col)
        self.old_files_tree.column(_("col_name"), width=500)
        self.old_files_tree.column(_("col_size_mb"), anchor='e', width=120)
        self.old_files_tree.column(_("col_last_access"), anchor='center', width=150)
        v_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.old_files_tree.yview)
        v_scroll.pack(side='right', fill='y')
        self.old_files_tree.configure(yscrollcommand=v_scroll.set)
        self.old_files_tree.pack(fill='both', expand=True)
        btn_frame = ttk.Frame(parent_tab)
        btn_frame.pack(fill='x', padx=5)
        self.btn_compress_old_files = ttk.Button(btn_frame, text=_("compress_selected"), command=self.compress_selected_old_files, state='disabled')
        self.btn_compress_old_files.pack(side='left', pady=5)

    def create_big_files_table(self, parent_tab):
        frame = ttk.Frame(parent_tab)
        frame.pack(fill='both', expand=True, padx=5, pady=5)
        cols = (_("col_name"), _("col_size_mb"), _("col_mdate"), _("col_fullpath"))
        self.big_files_tree = ttk.Treeview(frame, columns=cols, show='headings')
        for col in cols:
            self.big_files_tree.heading(col, text=col)
        self.big_files_tree.column(_("col_name"), width=250)
        self.big_files_tree.column(_("col_size_mb"), anchor='e', width=120)
        self.big_files_tree.column(_("col_mdate"), width=150)
        self.big_files_tree.column(_("col_fullpath"), width=400)
        v_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.big_files_tree.yview)
        h_scroll = ttk.Scrollbar(frame, orient="horizontal", command=self.big_files_tree.xview)
        self.big_files_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.pack(side='right', fill='y')
        h_scroll.pack(side='bottom', fill='x')
        self.big_files_tree.pack(fill='both', expand=True)
        
    def create_context_menu(self):
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label=_("open_location"), command=self.open_file_location)
        self.context_menu.add_separator()
        self.context_menu.add_command(label=_("open_file"), command=self.open_file)
        self.files_tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Button-3>", self.show_nav_context_menu)

    def show_context_menu(self, event):
        tree = event.widget
        item_id = tree.identify_row(event.y)
        if item_id:
            tree.selection_set(item_id)
            # Assume a coluna 4 (índice 3) é sempre o caminho completo
            item_path = tree.item(item_id)['values'][3]
            if os.path.isdir(item_path):
                self.context_menu.entryconfig(_("open_file"), state="disabled")
            else:
                self.context_menu.entryconfig(_("open_file"), state="normal")
            self.context_menu.post(event.x_root, event.y_root)

    def show_nav_context_menu(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self.tree.selection_set(item_id)
            self.context_menu.entryconfig(_("open_file"), state="disabled")
            self.context_menu.entryconfig(_("open_location"), label=_("open_folder"))
            self.context_menu.post(event.x_root, event.y_root)

    def open_file_location(self):
        try:
            tree = self.focus_get()
            if not isinstance(tree, ttk.Treeview) or not tree.selection(): return
            item_id = tree.selection()[0]
            
            values = tree.item(item_id)['values']
            item_path = values[0] if tree is self.tree else values[3]
            folder_path = os.path.dirname(item_path) if os.path.isfile(item_path) else item_path
            
            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder_path])
            else:
                subprocess.run(["xdg-open", folder_path])
        except Exception as e:
            messagebox.showerror(_("error_open_folder"), f"{_('error_open_folder')}\n{e}")

    def open_file(self):
        try:
            tree = self.focus_get()
            if tree is not self.files_tree or not tree.selection(): return
            item_id = tree.selection()[0]
            
            file_path = tree.item(item_id)['values'][3]
            if os.path.isfile(file_path):
                if sys.platform == "win32":
                    os.startfile(file_path)
                elif sys.platform == "darwin":
                    subprocess.run(["open", file_path])
                else:
                    subprocess.run(["xdg-open", file_path])
        except Exception as e:
            messagebox.showerror(_("error_open_file"), f"{_('error_open_file')}\n{e}")
    
    def populate_root_nodes(self):
        if sys.platform == "win32":
            import string
            drives = [f'{d}:\\' for d in string.ascii_uppercase if os.path.exists(f'{d}:')]
            for drive in drives:
                node = self.tree.insert('', 'end', text=drive, values=[drive, 'drive'])
                self.tree.insert(node, 'end')
        else:
            root_node = self.tree.insert('', 'end', text="/", values=["/", 'folder'])
            self.tree.insert(root_node, 'end')

    def on_tree_open(self, event):
        parent_id = self.tree.focus()
        parent_path = self.tree.item(parent_id)['values'][0]
        self.tree.delete(*self.tree.get_children(parent_id))
        try:
            for item in os.listdir(parent_path):
                full_path = os.path.join(parent_path, item)
                if os.path.isdir(full_path):
                    try:
                        os.listdir(full_path) 
                        node = self.tree.insert(parent_id, 'end', text=item, values=[full_path, 'folder'])
                        self.tree.insert(node, 'end') 
                    except PermissionError:
                        continue
        except PermissionError:
            pass

    def reset_view_state(self):
        if self.fig_canvas:
            self.fig_canvas.get_tk_widget().destroy()
        self.lbl_status.config(text=_("select_folder_prompt"))
        self.lbl_status.pack(pady=50)
        self.clear_filters()
        for tree in [self.files_tree, self.duplicates_tree, self.old_files_tree, self.big_files_tree]:
            tree.delete(*tree.get_children())
        # Desativar todos os botões de ação
        for btn in [self.btn_find_duplicates, self.btn_find_old_files, self.btn_find_big_files, self.btn_delete_duplicates, self.btn_compress_old_files, self.btn_export]:
             if btn.winfo_exists(): btn.config(state='disabled')

    def apply_filters(self):
        unit = self.filter_unit_var.get()
        multiplier = {"KB": 1024, "MB": 1024**2, "GB": 1024**3}[unit]
        try:
            min_size = float(self.filter_min_size_var.get() or 0) * multiplier
            max_size = float(self.filter_max_size_var.get() or float('inf')) * multiplier
        except ValueError:
            messagebox.showerror(_("error_value_title"), _("error_value_message"))
            return

        texto = self.filter_text_var.get().lower()
        exts = [ext for cat, var in self.category_vars.items() if var.get() for ext in self.category_map[cat]]
        
        all_content = pd.concat([self.df_folders, self.df_files], ignore_index=True)
        if all_content.empty:
            self.populate_file_list_table(all_content)
            return
            
        mask = pd.Series(True, index=all_content.index)
        if texto:
            mask &= all_content['path'].str.lower().str.contains(texto, na=False)
        if min_size > 0:
            mask &= all_content['size'] >= min_size
        if max_size != float('inf'):
            mask &= all_content['size'] <= max_size
        if exts:
            mask &= all_content['ext'].isin(exts)
            
        self.populate_file_list_table(all_content[mask])

    def clear_filters(self):
        self.filter_text_var.set("")
        self.filter_min_size_var.set("")
        self.filter_max_size_var.set("")
        for var in self.category_vars.values():
            var.set(False)
        self.apply_filters()

    def populate_file_list_table(self, dataframe):
        self.files_tree.delete(*self.files_tree.get_children())
        for _, row in dataframe.iterrows():
            name = row['name']
            size_mb = row['size'] / (1024*1024)
            mtime = datetime.fromtimestamp(row['mtime']).strftime('%Y-%m-%d %H:%M')
            self.files_tree.insert("", "end", values=(name, f"{size_mb:,.2f}", mtime, row['path']))

    def populate_duplicates_table(self):
        self.duplicates_tree.delete(*self.duplicates_tree.get_children())
        for i, group in enumerate(self.duplicate_groups):
            if not group: continue
            size_mb = os.path.getsize(group[0]) / (1024*1024)
            group_title = _("group_files").format(group_num=i + 1, count=len(group))
            parent = self.duplicates_tree.insert("", "end", iid=f"G{i}", values=(group_title, f"{size_mb:,.2f}"))
            for file_path in group:
                self.duplicates_tree.insert(parent, "end", values=(f"  └─ {file_path}", ""))

    def populate_old_files_table(self):
        self.old_files_tree.delete(*self.old_files_tree.get_children())
        self.old_files.sort(key=lambda x: x['atime'])
        for item in self.old_files:
            size_mb = item['size'] / (1024*1024)
            atime_str = datetime.fromtimestamp(item['atime']).strftime('%Y-%m-%d')
            self.old_files_tree.insert("", "end", values=(item['path'], f"{size_mb:,.2f}", atime_str), iid=item['path'])

    def populate_big_files_table(self):
        self.big_files_tree.delete(*self.big_files_tree.get_children())
        for item in self.big_files:
            name = os.path.basename(item['path'])
            size_mb = item['size'] / (1024*1024)
            mtime = datetime.fromtimestamp(item['mtime']).strftime('%Y-%m-%d %H:%M')
            self.big_files_tree.insert("", "end", values=(name, f"{size_mb:,.2f}", mtime, item['path']))

    def delete_selected_duplicates(self):
        selected_items = self.duplicates_tree.selection()
        files_to_delete = [self.duplicates_tree.item(item)['values'][0].strip().replace("└─ ", "") for item in selected_items if self.duplicates_tree.parent(item)]
        if not files_to_delete:
            messagebox.showwarning(_("delete_warning_title"), _("delete_warning_message"))
            return
        
        confirm_msg = _("delete_confirm_message").format(count=len(files_to_delete))
        if messagebox.askyesno(_("delete_confirm_title"), confirm_msg):
            deleted_count = 0
            for file in files_to_delete:
                try:
                    os.remove(file)
                    deleted_count +=1
                except Exception as e:
                    logging.error(f"Falha ao apagar ficheiro duplicado {file}", exc_info=True)
            messagebox.showinfo(_("delete_done_title"), _("delete_done_message").format(count=deleted_count))
            self.start_duplicate_search()

    def export_to_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if not path: return
        try:
            with pd.ExcelWriter(path) as writer:
                all_content = pd.concat([self.df_folders, self.df_files], ignore_index=True)
                if not all_content.empty:
                    all_content.to_excel(writer, sheet_name=_("list_tab"), index=False)
                if self.duplicate_groups:
                    pd.DataFrame(self.duplicate_groups).to_excel(writer, sheet_name=_("duplicates_tab"), index=False)
                if self.old_files:
                    pd.DataFrame(self.old_files).to_excel(writer, sheet_name=_("old_files_tab"), index=False)
            logging.info(f"Resultados exportados com sucesso para {path}")
            messagebox.showinfo(_("export_success_title"), _("export_success_message").format(path=path))
        except Exception as e:
            logging.error(f"Erro ao exportar para Excel em {path}", exc_info=True)
            messagebox.showerror(_("export_error_title"), _("export_error_message"))

    def compress_selected_old_files(self):
        selected_iids = self.old_files_tree.selection()
        if not selected_iids:
            messagebox.showwarning(_("compress_no_selection_title"), _("compress_no_selection_message"))
            return
            
        confirm_msg = _("compress_confirm_message").format(count=len(selected_iids))
        if not messagebox.askyesno(_("compress_confirm_title"), confirm_msg):
            return
        
        files_to_compress = [self.old_files_tree.item(iid)['values'][0] for iid in selected_iids]
        save_path = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("ZIP archive", "*.zip")])
        if not save_path: return
        
        self.threaded_task(self.run_compression_and_deletion, files_to_compress, save_path)

    def run_compression_and_deletion(self, app_instance, file_list, zip_path):
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in file_list:
                    if os.path.exists(file_path):
                        zf.write(file_path, arcname=os.path.basename(file_path))
            
            deleted_count = 0
            for file_path in file_list:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    logging.error(f"Falha ao apagar {file_path}", exc_info=True)
            
            success_msg = _("compress_success_message").format(count=deleted_count)
            app_instance.after(0, lambda: messagebox.showinfo(_("export_success_title"), success_msg))
            app_instance.after(0, app_instance.start_old_files_search)
        except Exception as e:
            logging.error(f"Erro fatal durante a compressão para {zip_path}", exc_info=True)
            app_instance.after(0, lambda: messagebox.showerror(_("compress_error_title"), _("export_error_message")))

    def export_to_pdf(self):
        if self.df_files.empty and self.df_folders.empty:
            messagebox.showwarning(_("delete_warning_title"), "Não há dados para exportar. Faça uma análise primeiro.")
            return

        save_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Document", "*.pdf")])
        if not save_path: return

        chart_path = "temp_chart.png"
        try:
            if self.fig_canvas:
                self.fig_canvas.figure.savefig(chart_path, facecolor=self.COLOR_BACKGROUND, bbox_inches='tight')
            
            all_content = pd.concat([self.df_folders, self.df_files], ignore_index=True)
            utils.export_report_pdf(all_content, chart_path, save_path, self.storage_summary)
            
            messagebox.showinfo(_("export_success_title"), _("export_success_message").format(path=save_path))

        except Exception as e:
            logging.error(f"Erro ao exportar PDF: {e}", exc_info=True)
            messagebox.showerror(_("export_error_title"), _("export_error_message"))
        finally:
            if os.path.exists(chart_path):
                os.remove(chart_path)

    def get_status_label(self):
        try:
            current_tab_text = self.notebook.tab(self.notebook.select(), "text")
            if current_tab_text == _("duplicates_tab"):
                return ttk.Label(self.duplicates_tab)
            elif current_tab_text == _("old_files_tab"):
                return ttk.Label(self.old_files_tab)
            else:
                return self.lbl_status
        except tk.TclError:
            return self.lbl_status

    def set_determinate_progress(self, max_value):
        self.progress_bar.config(mode='determinate', maximum=max_value, value=0)

    def update_progress_value(self, value):
        self.progress_bar['value'] = value

    def set_ui_busy(self, is_busy: bool):
        cursor = "watch" if is_busy else ""
        self.config(cursor=cursor)
        state = 'disabled' if is_busy else 'normal'
        
        if is_busy:
            self.tree.unbind("<<TreeviewSelect>>")
            # Deixa a barra de progresso no modo indeterminado por padrão
            self.progress_bar.config(mode='indeterminate')
        else:
            self.tree.bind("<<TreeviewSelect>>", self.on_folder_select)
            
        # *** CORREÇÃO AQUI ***
        # Adicionado o novo botão à lista de botões a serem geridos.
        buttons_to_manage = [
            self.btn_find_duplicates, self.btn_find_old_files, self.btn_find_big_files,
            self.btn_delete_duplicates, self.btn_compress_old_files, self.btn_export
        ]
        for btn in buttons_to_manage:
            if btn.winfo_exists(): btn.config(state=state)
        
        if not is_busy and not os.path.isdir(self.current_path.get()):
             for btn in [self.btn_find_duplicates, self.btn_find_old_files, self.btn_find_big_files, self.btn_export]:
                 if btn.winfo_exists(): btn.config(state='disabled')
            
        self.update_idletasks()
        
        if is_busy:
            self.progress_bar.pack(fill='x', padx=10, pady=5, side='bottom')
            if self.progress_bar['mode'] == 'indeterminate':
                self.progress_bar.start(10)
        else:
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
        
    def threaded_task(self, func, *args):
        self.set_ui_busy(True)
        thread = threading.Thread(target=self.run_task_wrapper, args=(func, self, *args), daemon=True)
        thread.start()

    def run_task_wrapper(self, func, *args):
        try:
            func(*args)
        except Exception as e:
            logging.error(f"Erro na thread da função {func.__name__}", exc_info=True)
            self.after(0, lambda: messagebox.showerror(_("export_error_title"), _("export_error_message")))
        finally:
            self.after(0, self.set_ui_busy, False)

    def on_folder_select(self, event):
        if not self.tree.selection(): return
        folder_id = self.tree.selection()[0]
        folder_path = self.tree.item(folder_id)['values'][0]
        self.current_path.set(folder_path)
        self.reset_view_state()
        self.lbl_status.config(text=_("analyzing").format(folder=os.path.basename(folder_path)))
        self.lbl_status.pack(pady=50)
        self.threaded_task(analysis.run_quick_analysis, folder_path)

    def start_duplicate_search(self):
        path = self.current_path.get()
        if not os.path.isdir(path): return
        self.get_status_label().config(text=_("searching_duplicates"))
        self.notebook.select(self.duplicates_tab)
        self.threaded_task(analysis.run_duplicate_analysis, path)

    def start_old_files_search(self):
        days_prompt = _("old_files_prompt") 
        days = simpledialog.askinteger(_("old_files_found_title"), days_prompt, initialvalue=180, minvalue=1, parent=self)
        if not days: return
        path = self.current_path.get()
        if not os.path.isdir(path): return
        self.get_status_label().config(text=_("searching_old_files").format(days=days))
        self.notebook.select(self.old_files_tab)
        self.threaded_task(analysis.run_old_files_analysis, path, days)

    def start_big_files_search(self):
        path = self.current_path.get()
        if not os.path.isdir(path): return
        
        top_n = simpledialog.askinteger(_("big_files_tab"), _("big_files_prompt"), initialvalue=50, minvalue=10, parent=self)
        if not top_n: return

        self.notebook.select(self.big_files_tab)
        self.threaded_task(analysis.run_big_files_analysis, path, top_n)
        
    def update_quick_analysis_view(self):
        # Ativa os botões de ação principais
        for btn in [self.btn_find_duplicates, self.btn_find_old_files, self.btn_find_big_files, self.btn_export]:
             if btn.winfo_exists(): btn.config(state='normal')
        
        all_content = pd.concat([self.df_folders, self.df_files], ignore_index=True)
        if all_content.empty:
            self.lbl_status.config(text=_("empty_folder"))
            self.set_ui_busy(False)
            return
            
        self.apply_filters()
        self.update_pie_chart()
        # Inicia o cálculo do resumo após a análise rápida
        self.threaded_task(analysis.compute_storage_summary)
        
    def update_pie_chart(self):
        if self.fig_canvas:
            self.fig_canvas.get_tk_widget().destroy()
        self.lbl_status.pack_forget()

        chart_data = pd.concat([self.df_folders, self.df_files], ignore_index=True)
        if chart_data.empty: return

        top_n = 7
        df_plot = chart_data.nlargest(top_n, 'size').copy()
        
        if len(chart_data) > top_n:
            outros_size = chart_data.nsmallest(len(chart_data) - top_n, 'size')['size'].sum()
            outros_row = pd.DataFrame([{'name': _("chart_others"), 'size': outros_size}])
            df_plot = pd.concat([df_plot, outros_row], ignore_index=True)

        total_size = chart_data['size'].sum()
        if total_size == 0: return

        labels_for_legend = [f"{row['name']} ({row['size']/total_size:.1%})" for _, row in df_plot.iterrows()]

        plt.style.use('seaborn-v0_8-deep')
        fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
        fig.patch.set_facecolor(self.COLOR_BACKGROUND)
        ax.set_facecolor(self.COLOR_BACKGROUND)

        fig.subplots_adjust(left=0.05, right=0.7)

        wedges, texts = ax.pie(df_plot['size'], startangle=90, wedgeprops=dict(width=0.4, edgecolor=self.COLOR_BACKGROUND), radius=1.2)
        
        legend = ax.legend(wedges, labels_for_legend,
                  title=_("chart_legend_title"),
                  loc="center left",
                  bbox_to_anchor=(1, 0, 0.5, 1),
                  fontsize='medium',
                  facecolor=self.COLOR_BACKGROUND,
                  edgecolor=self.COLOR_BACKGROUND)
        
        for text in legend.get_texts():
            text.set_color(self.COLOR_TEXT)
        legend.get_title().set_color(self.COLOR_TEXT)
        
        title_text = _("chart_title").format(folder=os.path.basename(self.current_path.get()))
        ax.set_title(title_text, pad=20, fontdict={'fontsize': 14, 'color': self.COLOR_TEXT})
        
        self.fig_canvas = FigureCanvasTkAgg(fig, master=self.chart_tab)
        self.fig_canvas.draw()
        self.fig_canvas.get_tk_widget().pack(fill='both', expand=True, padx=5, pady=5)

    def update_duplicates_view(self):
        self.get_status_label().config(text="")
        self.populate_duplicates_table()
        if self.duplicate_groups:
            self.btn_delete_duplicates.config(state='normal')
            messagebox.showinfo(_("duplicates_found_title"), _("duplicates_found_message").format(count=len(self.duplicate_groups)))
        else:
            messagebox.showinfo(_("no_duplicates_title"), _("no_duplicates_message"))

    def update_old_files_view(self):
        self.get_status_label().config(text="")
        self.populate_old_files_table()
        if self.old_files:
            self.btn_compress_old_files.config(state='normal')
            messagebox.showinfo(_("old_files_found_title"), _("old_files_found_message").format(count=len(self.old_files)))
        else:
            messagebox.showinfo(_("old_files_found_title"), _("no_old_files_found_message"))
    
    def update_big_files_view(self):
        self.get_status_label().config(text="")
        self.populate_big_files_table()

    def update_storage_summary_view(self):
        summary = self.storage_summary
        self.lbl_total_files.config(text=f"{_('total_files')} {summary.get('total_files', 0)}")
        self.lbl_total_size.config(text=f"{_('total_size_gb')} {summary.get('total_size_gb', 0):.2f} GB")
        self.lbl_avg_size.config(text=f"{_('avg_size_mb')} {summary.get('avg_size_mb', 0):.2f} MB")
