"""
Settings Panel — Interface graphique pour les paramètres (tkinter).
"""

import os
import platform
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from app.settings import Settings
from app.ai_providers import PROVIDERS


class SettingsPanel(ttk.Frame):
    """Panneau de paramètres de l'application."""

    def __init__(self, parent, settings: Settings):
        super().__init__(parent)
        self.settings = settings
        self.settings_changed_callback = None
        self._setup_ui()

    def set_settings_changed_callback(self, callback):
        self.settings_changed_callback = callback

    def _setup_ui(self):
        style = ttk.Style()
        style.configure("Settings.TFrame", background="#1E1E1E")
        self.configure(style="Settings.TFrame")

        # Scrollable container (using Canvas)
        canvas = tk.Canvas(self, bg="#1E1E1E", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        
        self.scrollable_frame = ttk.Frame(canvas, style="Settings.TFrame")
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=800)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=20)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # --- Title ---
        tk.Label(self.scrollable_frame, text="⚙️  Paramètres", bg="#1E1E1E", fg="#FFFFFF", 
                 font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(0, 5))
        tk.Label(self.scrollable_frame, text="Configure tes clés API et tes préférences", 
                 bg="#1E1E1E", fg="#999999", font=("Segoe UI", 14)).pack(anchor="w", pady=(0, 20))

        # --- Theme ---
        theme_group = self._create_group("🎨  Thème", "Choisis le thème de l'application (Nécessite un redémarrage)")
        
        self.theme_var = tk.StringVar(value=self.settings.get_theme())
        themes = ["dark", "light", "sepia", "hacker"]
        combo_theme = ttk.Combobox(theme_group, textvariable=self.theme_var, values=themes, state="readonly", font=("Segoe UI", 13))
        combo_theme.pack(anchor="w", pady=10)

        # --- API Keys ---
        api_group = self._create_group("🔑  Clés API", "Les clés API sont gérées dans un fichier texte séparé.")
        
        btn_open_api = tk.Button(api_group, text="Ouvrir api_keys.txt", bg="#333333", fg="#E0E0E0",
                                font=("Segoe UI", 13), cursor="hand2", bd=0, padx=15, pady=8,
                                command=self._open_api_keys)
        btn_open_api.pack(anchor="w", pady=10)

        # --- Default Provider ---
        provider_group = self._create_group("🤖  Provider par défaut", "Choisis le provider IA utilisé par défaut")
        
        self.default_provider_var = tk.StringVar()
        providers = ["— Aucun —"] + list(PROVIDERS.keys())
        current_default = self.settings.get_default_provider()
        self.default_provider_var.set(current_default if current_default else "— Aucun —")
        
        combo_default = ttk.Combobox(provider_group, textvariable=self.default_provider_var, values=providers, state="readonly", font=("Segoe UI", 13))
        combo_default.pack(anchor="w", pady=10)

        # --- Model Selection ---
        model_group = self._create_group("🧠  Modèles IA", "Sélectionne le modèle pour chaque provider")
        
        self.model_vars = {}
        for provider_name, provider_cls in PROVIDERS.items():
            row = tk.Frame(model_group, bg="#252526")
            row.pack(fill=tk.X, pady=5)
            
            tk.Label(row, text=provider_name, bg="#252526", fg="#E0E0E0", width=15, anchor="w", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT)
            
            var = tk.StringVar()
            temp_prov = provider_cls("")
            models = temp_prov.get_available_models()
            current_model = self.settings.get_model(provider_name)
            var.set(current_model if current_model in models else models[0])
            
            combo = ttk.Combobox(row, textvariable=var, values=models, state="readonly", width=30, font=("Segoe UI", 13))
            combo.pack(side=tk.LEFT, padx=10)
            self.model_vars[provider_name] = var

        # --- Save Button ---
        btn_save = tk.Button(self.scrollable_frame, text="💾 Sauvegarder les paramètres", bg="#0A84FF", fg="white",
                            font=("Segoe UI", 14, "bold"), cursor="hand2", bd=0, padx=20, pady=10,
                            activebackground="#0063CC", activeforeground="white", command=self._save_settings)
        btn_save.pack(pady=30)

    def _create_group(self, title, desc):
        group = tk.Frame(self.scrollable_frame, bg="#252526", bd=1, relief=tk.SOLID, highlightbackground="#3C3C3C", highlightthickness=1)
        group.pack(fill=tk.X, pady=10, padx=5, ipady=10)
        
        inner = tk.Frame(group, bg="#252526", padx=15, pady=5)
        inner.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(inner, text=title, bg="#252526", fg="#0A84FF", font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 5))
        tk.Label(inner, text=desc, bg="#252526", fg="#999999", font=("Segoe UI", 12)).pack(anchor="w", pady=(0, 5))
        
        return inner

    def _open_api_keys(self):
        filepath = os.path.join(self.settings.app_dir, "api_keys.txt")
        if not os.path.exists(filepath):
            self.settings.load() # Creates the template if missing
            
        try:
            os.startfile(filepath)
        except Exception:
            pass

    def _save_settings(self):
        # Save theme
        self.settings.set_theme(self.theme_var.get())

        # Save default provider
        default_p = self.default_provider_var.get()
        if default_p == "— Aucun —":
            self.settings.set_default_provider("")
        else:
            self.settings.set_default_provider(default_p)

        # Save models
        for provider, var in self.model_vars.items():
            self.settings.set_model(provider, var.get())

        self.settings.save()
        
        if self.settings_changed_callback:
            self.settings_changed_callback()
            
        messagebox.showinfo("Sauvegardé", "Les paramètres ont été sauvegardés avec succès ! ✅")
