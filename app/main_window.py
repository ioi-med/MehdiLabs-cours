"""
Main Window — Fenêtre principale de l'application (tkinter, version Windows).
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox

from app.settings import Settings
from app.file_manager import FileManager
from app.editor import Editor
from app.chatbot import Chatbot
from app.settings_panel import SettingsPanel
from app.dashboard import Dashboard


class MainWindow(tk.Tk):
    """Fenêtre principale de l'application MehdiLabs Cours."""

    def __init__(self, app_dir: str, cours_dir: str):
        super().__init__()
        self.app_dir = app_dir
        self.cours_dir = cours_dir
        self.settings = Settings(app_dir)

        self.title("MehdiLabs Cours")
        self.geometry("1400x850")
        self.minsize(1100, 700)
        
        # Apply theme
        self._apply_theme()
        
        # Set icon if exists
        try:
            ico_path = os.path.join(app_dir, "assets", "icon.ico")
            if os.path.exists(ico_path):
                self.iconbitmap(ico_path)
        except Exception:
            pass

        self._setup_ui()
        self._setup_shortcuts()
        
        # Session Restore
        last_file = self.settings.get_last_opened_file()
        if last_file and os.path.exists(last_file):
            self._set_active_page(1) # Mes cours
            self.editor.open_file(last_file)
        else:
            self._set_active_page(0) # Dashboard
            
        self._update_status()

    def _apply_theme(self):
        theme = self.settings.get_theme()
        if theme == "light":
            self.colors = {
                "bg_main": "#F5F5F7",
                "bg_sidebar": "#E5E5EA",
                "bg_secondary": "#FFFFFF",
                "fg_primary": "#000000",
                "fg_secondary": "#666666",
                "accent": "#0A84FF",
                "accent_hover": "#0063CC",
                "border": "#D1D1D6"
            }
        elif theme == "sepia":
            self.colors = {
                "bg_main": "#F4ECD8",
                "bg_sidebar": "#E8DEC5",
                "bg_secondary": "#FAF5E9",
                "fg_primary": "#433422",
                "fg_secondary": "#7D6B56",
                "accent": "#D97D54",
                "accent_hover": "#B8653F",
                "border": "#D5C9B3"
            }
        elif theme == "hacker":
            self.colors = {
                "bg_main": "#0D1117",
                "bg_sidebar": "#010409",
                "bg_secondary": "#161B22",
                "fg_primary": "#00FF00",
                "fg_secondary": "#008800",
                "accent": "#00FF00",
                "accent_hover": "#00CC00",
                "border": "#30363D"
            }
        else: # dark
            self.colors = {
                "bg_main": "#1E1E1E",
                "bg_sidebar": "#252526",
                "bg_secondary": "#333333",
                "fg_primary": "#FFFFFF",
                "fg_secondary": "#999999",
                "accent": "#0A84FF",
                "accent_hover": "#0058D0",
                "border": "#3C3C3C"
            }
        self.configure(bg=self.colors["bg_main"])

    def _setup_ui(self):
        # Configure global styles
        style = ttk.Style()
        style.theme_use('default')
        
        # We use standard tk Frames for main layout for better color control
        main_frame = tk.Frame(self, bg=self.colors["bg_main"])
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Sidebar ---
        sidebar = tk.Frame(main_frame, bg=self.colors["bg_sidebar"], width=240)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        # App Title
        title_frame = tk.Frame(sidebar, bg=self.colors["bg_sidebar"])
        title_frame.pack(fill=tk.X, pady=(20, 10), padx=16)
        tk.Label(title_frame, text="MehdiLabs", bg=self.colors["bg_sidebar"], fg=self.colors["accent"], font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(title_frame, text="C O U R S", bg=self.colors["bg_sidebar"], fg=self.colors["fg_secondary"], font=("Segoe UI", 12, "bold"), ).pack(anchor="w")

        # Separator
        sep = tk.Frame(sidebar, bg=self.colors["border"], height=1)
        sep.pack(fill=tk.X, padx=16, pady=(0, 10))

        # Nav Buttons
        self.nav_buttons = []
        
        def create_nav_btn(text, page_index):
            btn = tk.Button(sidebar, text=text, bg=self.colors["bg_sidebar"], fg=self.colors["fg_secondary"], font=("Segoe UI", 15),
                           bd=0, anchor="w", padx=20, pady=12, cursor="hand2",
                           activebackground=self.colors["bg_secondary"], activeforeground=self.colors["fg_primary"],
                           command=lambda: self._set_active_page(page_index))
            btn.pack(fill=tk.X, padx=8, pady=2)
            self.nav_buttons.append(btn)
            return btn

        create_nav_btn("📊  Dashboard", 0)
        create_nav_btn("📁  Mes cours", 1)
        create_nav_btn("💬  Chat IA", 2)
        create_nav_btn("⚙️  Paramètres", 3)

        # NotebookLM Link
        import webbrowser
        btn_notebook = tk.Label(sidebar, text="🔗 NoteBookLM", bg=self.colors["bg_sidebar"], fg=self.colors["accent"], font=("Segoe UI", 13, "underline"), cursor="hand2")
        btn_notebook.pack(side=tk.BOTTOM, anchor="w", padx=16, pady=(0, 10))
        btn_notebook.bind("<Button-1>", lambda e: webbrowser.open("https://notebooklm.google.com/"))
        
        # Quit Button
        btn_quit = tk.Button(sidebar, text="❌ Quitter", bg=self.colors["bg_sidebar"], fg="#FF453A", font=("Segoe UI", 13, "bold"),
                           bd=0, anchor="w", cursor="hand2", activebackground=self.colors["bg_secondary"], activeforeground="#FF6961",
                           command=self._on_closing)
        btn_quit.pack(side=tk.BOTTOM, anchor="w", padx=12, pady=(0, 5))

        # Version
        tk.Label(sidebar, text="v1.0.0 (Windows)", bg=self.colors["bg_sidebar"], fg=self.colors["fg_secondary"], font=("Segoe UI", 11)).pack(side=tk.BOTTOM, anchor="w", padx=16, pady=(16, 0))

        # --- Content Area (Stacked) ---
        self.content_area = tk.Frame(main_frame, bg=self.colors["bg_main"])
        self.content_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Page 0: Dashboard
        self.page_dashboard = Dashboard(self.content_area, self.cours_dir)

        # Page 1: Files (File Manager + Editor)
        self.page_files = tk.Frame(self.content_area, bg=self.colors["bg_main"])
        
        self.paned_files = ttk.PanedWindow(self.page_files, orient=tk.HORIZONTAL)
        self.paned_files.pack(fill=tk.BOTH, expand=True)
        
        self.file_manager = FileManager(self.paned_files, self.cours_dir, self.settings)
        self.paned_files.add(self.file_manager, weight=0)
        
        self.editor = Editor(self.paned_files, self.settings)
        self.paned_files.add(self.editor, weight=1)
        
        # Connect File Manager -> Editor
        self.file_manager.set_callbacks(
            on_double_click=self.editor.open_file
        )
        self.editor.set_content_changed_callback(self._update_status)

        # Page 2: Chatbot
        self.page_chat = Chatbot(self.content_area, self.settings, self.cours_dir)

        # Page 3: Settings
        self.page_settings = SettingsPanel(self.content_area, self.settings)
        self.page_settings.set_settings_changed_callback(self._on_settings_changed)

        self.pages = [self.page_dashboard, self.page_files, self.page_chat, self.page_settings]

        # --- Status Bar ---
        self.status_bar = tk.Frame(self, bg=self.colors["bg_sidebar"], height=30)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar.pack_propagate(False)
        
        # Add top border to status bar
        tk.Frame(self.status_bar, bg=self.colors["border"], height=1).pack(fill=tk.X, side=tk.TOP)
        
        self.status_label = tk.Label(self.status_bar, text="", bg=self.colors["bg_sidebar"], fg=self.colors["fg_secondary"], font=("Segoe UI", 11))
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # Pomodoro
        self.pomodoro_time = 25 * 60
        self.pomodoro_running = False
        self.pomodoro_id = None
        
        self.pomo_btn = tk.Button(self.status_bar, text="🍅 25:00", bg=self.colors["bg_sidebar"], fg=self.colors["fg_secondary"],
                                 bd=0, font=("Segoe UI", 11, "bold"), cursor="hand2", command=self._toggle_pomodoro)
        self.pomo_btn.pack(side=tk.LEFT, padx=20)
        
        self.provider_status = tk.Label(self.status_bar, text="", bg=self.colors["bg_sidebar"], fg=self.colors["fg_secondary"], font=("Segoe UI", 11))
        self.provider_status.pack(side=tk.RIGHT, padx=10)

        # Bind close event
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _setup_shortcuts(self):
        """Configure les raccourcis clavier globaux (Ctrl pour Windows)."""
        self.bind("<Control-question>", lambda e: self._show_shortcuts_help())
        self.bind("<Control-Key-1>", lambda e: self._set_active_page(0))
        self.bind("<Control-Key-2>", lambda e: self._set_active_page(1))
        self.bind("<Control-Key-3>", lambda e: self._set_active_page(2))
        self.bind("<Control-Key-4>", lambda e: self._set_active_page(3))
        self.bind("<Control-F>", lambda e: self._show_global_search())
        
    def _show_shortcuts_help(self):
        """Affiche une fenêtre avec tous les raccourcis clavier."""
        win = tk.Toplevel(self)
        win.title("Raccourcis clavier")
        win.geometry("400x500")
        win.configure(bg=self.colors["bg_main"])
        win.transient(self)
        
        tk.Label(win, text="⌨️ Raccourcis clavier", bg=self.colors["bg_main"], fg=self.colors["fg_primary"], 
                 font=("Segoe UI", 18, "bold")).pack(pady=(20, 10))
                 
        shortcuts = [
            ("Global", ""),
            ("Ctrl + 1", "Ouvrir Dashboard"),
            ("Ctrl + 2", "Ouvrir Mes cours"),
            ("Ctrl + 3", "Ouvrir Chat IA"),
            ("Ctrl + 4", "Ouvrir Paramètres"),
            ("Ctrl + ?", "Afficher cette aide"),
            ("", ""),
            ("Éditeur", ""),
            ("Ctrl + S", "Sauvegarder le fichier"),
            ("Ctrl + F", "Rechercher / Remplacer"),
            ("Ctrl + B", "Mettre en gras"),
            ("Ctrl + I", "Mettre en italique"),
        ]
        
        frame = tk.Frame(win, bg=self.colors["bg_main"])
        frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        for keys, desc in shortcuts:
            if not keys:
                tk.Frame(frame, bg=self.colors["bg_main"], height=10).pack(fill=tk.X)
            elif not desc:
                tk.Label(frame, text=keys, bg=self.colors["bg_main"], fg=self.colors["accent"], font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(10, 5))
            else:
                row = tk.Frame(frame, bg=self.colors["bg_main"])
                row.pack(fill=tk.X, pady=2)
                tk.Label(row, text=keys, bg=self.colors["bg_secondary"], fg=self.colors["fg_primary"], font=("Consolas", 12), padx=8, pady=2).pack(side=tk.LEFT)
                tk.Label(row, text=desc, bg=self.colors["bg_main"], fg=self.colors["fg_secondary"], font=("Segoe UI", 12)).pack(side=tk.RIGHT)
                
        tk.Button(win, text="Fermer", bg=self.colors["accent"], fg="white", bd=0, cursor="hand2", padx=20, pady=8, command=win.destroy).pack(pady=20)

    def _set_active_page(self, index: int):
        # Update buttons
        for i, btn in enumerate(self.nav_buttons):
            if i == index:
                btn.config(bg=self.colors["accent_hover"], fg="white" if self.settings.get_theme()=="light" else self.colors["accent"])
            else:
                btn.config(bg=self.colors["bg_sidebar"], fg=self.colors["fg_secondary"])

        # Update pages
        for i, page in enumerate(self.pages):
            if i == index:
                page.pack(fill=tk.BOTH, expand=True)
                if i == 0:  # Dashboard
                    self.page_dashboard.refresh_stats()
            else:
                page.pack_forget()
                
        self._update_status()

    def _update_status(self):
        dirs, files = self.file_manager.get_file_count()
        self.status_label.config(text=f"📁 {dirs} matières • {files} fichiers")

        configured = self.settings.get_configured_providers()
        if configured:
            default = self.settings.get_default_provider()
            if default:
                self.provider_status.config(text=f"🤖 {default}")
            else:
                self.provider_status.config(text=f"🤖 {len(configured)} provider(s) configuré(s)")
        else:
            self.provider_status.config(text="⚠️ Aucun provider configuré")

    def _on_settings_changed(self):
        self.settings.load()
        self._update_status()
        
        # Check if theme changed (requires restart message in tkinter usually, but we can show a prompt)
        messagebox.showinfo("Thème modifié", "Veuillez redémarrer l'application pour appliquer complètement le nouveau thème.", parent=self)

    def _toggle_pomodoro(self):
        if self.pomodoro_running:
            self.pomodoro_running = False
            if self.pomodoro_id:
                self.after_cancel(self.pomodoro_id)
                self.pomodoro_id = None
            self.pomo_btn.config(fg=self.colors["fg_secondary"])
        else:
            self.pomodoro_running = True
            self.pomo_btn.config(fg="#FF453A")
            self._update_pomodoro()

    def _update_pomodoro(self):
        if not self.pomodoro_running:
            return
            
        if self.pomodoro_time > 0:
            self.pomodoro_time -= 1
            mins = self.pomodoro_time // 60
            secs = self.pomodoro_time % 60
            self.pomo_btn.config(text=f"🍅 {mins:02d}:{secs:02d}")
            self.pomodoro_id = self.after(1000, self._update_pomodoro)
        else:
            self.pomodoro_running = False
            self.pomodoro_time = 25 * 60
            self.pomo_btn.config(text="🍅 25:00", fg=self.colors["fg_secondary"])
            
            # Windows notification via PowerShell toast
            try:
                import subprocess
                ps_script = (
                    "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
                    "ContentType = WindowsRuntime] > $null; "
                    "$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
                    "[Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
                    "$textNodes = $template.GetElementsByTagName('text'); "
                    "$textNodes.Item(0).AppendChild($template.CreateTextNode('Pomodoro terminé')) > $null; "
                    "$textNodes.Item(1).AppendChild($template.CreateTextNode('Bravo ! Prends 5 minutes de pause.')) > $null; "
                    "$toast = [Windows.UI.Notifications.ToastNotification]::new($template); "
                    "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('MehdiLabs Cours').Show($toast)"
                )
                subprocess.Popen(["powershell", "-Command", ps_script], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            messagebox.showinfo("Pomodoro", "Temps écoulé ! Prends une pause de 5 minutes.")

    def _show_global_search(self):
        """Recherche globale dans tous les cours."""
        win = tk.Toplevel(self)
        win.title("Recherche Globale")
        win.geometry("600x400")
        win.configure(bg=self.colors["bg_main"])
        win.transient(self)
        
        top_frame = tk.Frame(win, bg=self.colors["bg_main"])
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(top_frame, text="🔍", bg=self.colors["bg_main"], fg=self.colors["fg_primary"], font=("Segoe UI", 16)).pack(side=tk.LEFT)
        search_var = tk.StringVar()
        search_entry = tk.Entry(top_frame, textvariable=search_var, bg=self.colors["bg_secondary"], fg=self.colors["fg_primary"],
                               insertbackground=self.colors["fg_primary"], font=("Segoe UI", 14), width=30)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        search_entry.focus_set()
        
        listbox = tk.Listbox(win, bg=self.colors["bg_sidebar"], fg=self.colors["fg_primary"], font=("Segoe UI", 13),
                            bd=0, highlightthickness=0, selectbackground=self.colors["accent_hover"])
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        results_paths = []
        
        def do_search(*args):
            query = search_var.get().lower()
            listbox.delete(0, tk.END)
            results_paths.clear()
            if len(query) < 2: return
            
            import os
            for root, dirs, files in os.walk(self.cours_dir):
                if ".chat_history" in root or ".trash" in root or ".backups" in root: continue
                for f in files:
                    if not f.endswith(".md"): continue
                    filepath = os.path.join(root, f)
                    try:
                        with open(filepath, "r", encoding="utf-8") as file:
                            content = file.read().lower()
                            if query in content:
                                rel_path = os.path.relpath(filepath, self.cours_dir)
                                listbox.insert(tk.END, f"📄 {rel_path}")
                                results_paths.append(filepath)
                    except: pass
                    
        search_var.trace_add("write", do_search)
        
        def on_select(event):
            selection = listbox.curselection()
            if selection:
                filepath = results_paths[selection[0]]
                self._set_active_page(1) # Go to Mes cours
                self.editor.open_file(filepath)
                win.destroy()
                
        listbox.bind("<Double-1>", on_select)
        listbox.bind("<Return>", on_select)

    def _on_closing(self):
        if self.editor.current_file and self.editor._modified:
            self.editor.save_file()
        self.destroy()
