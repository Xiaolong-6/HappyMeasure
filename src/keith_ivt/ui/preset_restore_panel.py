from __future__ import annotations

from tkinter import StringVar, END
from tkinter import ttk

from keith_ivt.data.backup import default_backup_dir


class PresetRestorePanelMixin:
    def _build_preset_panel(self, parent) -> None:
        self._section_title(parent, "Preset")
        box = ttk.Frame(parent, style="Card.TFrame", padding=(10, 8))
        box.pack(fill="both", expand=True, padx=10, pady=8)
        box.rowconfigure(1, weight=1)
        box.columnconfigure(0, weight=1)
        
        # Buttons on top so they're always visible even in small windows
        btns = ttk.Frame(box)
        btns.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        for i in range(4):
            btns.columnconfigure(i, weight=1, uniform="preset_actions")
        for i, (text, cmd) in enumerate([("Refresh", self.refresh_preset_list), ("Load", self.load_selected_preset), ("Save As...", self.save_named_preset_dialog), ("Delete", self.delete_selected_preset)]):
            ttk.Button(btns, text=text, style="Soft.TButton", command=cmd).grid(row=0, column=i, sticky="ew", padx=3)
        
        # Treeview below buttons with weight=1 to fill remaining space
        self.preset_list = ttk.Treeview(box, columns=("name",), show="headings", selectmode="browse")
        self.preset_list.heading("name", text="Preset name")
        self.preset_list.column("name", stretch=True)
        self.preset_list.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.refresh_preset_list()

    def _build_restore_panel(self, parent) -> None:
        self._section_title(parent, "Restore")
        box = ttk.Frame(parent, padding=(10, 8))
        box.pack(fill="both", expand=True, padx=10, pady=4)
        box.rowconfigure(2, weight=1)
        box.columnconfigure(0, weight=1)
        
        self.backup_folder_var = StringVar(value=str(default_backup_dir()))
        folder_row = ttk.Frame(box)
        folder_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        folder_row.columnconfigure(1, weight=1)
        ttk.Label(folder_row, text="Backup folder", style="Card.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Entry(folder_row, textvariable=self.backup_folder_var).grid(row=0, column=1, sticky="ew")
        ttk.Button(folder_row, text="Browse...", style="Soft.TButton", command=self.choose_backup_folder).grid(row=0, column=2, padx=(6, 0))
        btns = ttk.Frame(box)
        btns.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        for col in range(3):
            btns.columnconfigure(col, weight=1, uniform="restore_actions")
        ttk.Button(btns, text="Refresh", style="Soft.TButton", command=self.refresh_backup_list).grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=(0, 4))
        ttk.Button(btns, text="Import", style="Soft.TButton", command=self.import_selected_backup).grid(row=0, column=1, sticky="ew", padx=4, pady=(0, 4))
        ttk.Button(btns, text="Open", style="Soft.TButton", command=self.open_backup_folder).grid(row=0, column=2, sticky="ew", padx=(4, 0), pady=(0, 4))
        self.backup_tree = ttk.Treeview(box, columns=("file", "size", "modified"), show="headings", height=8, selectmode="browse")
        self.backup_tree.heading("file", text="Backup file")
        self.backup_tree.heading("size", text="Size")
        self.backup_tree.heading("modified", text="Modified")
        self.backup_tree.column("file", width=210, stretch=True)
        self.backup_tree.column("size", width=70, stretch=False, anchor="e")
        self.backup_tree.column("modified", width=140, stretch=False)
        self.backup_tree.grid(row=2, column=0, sticky="nsew")
        y = ttk.Scrollbar(box, orient="vertical", command=self.backup_tree.yview)
        y.grid(row=2, column=1, sticky="ns")
        self.backup_tree.configure(yscrollcommand=y.set)
        self.backup_tree.bind("<Double-1>", lambda _e: self.import_selected_backup())
        self.backup_tree.bind("<Button-3>", self._show_backup_context_menu)
        ttk.Label(box, textvariable=self.backup_text, style="Muted.TLabel").grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.ensure_sample_backups()
        self.refresh_backup_list()
