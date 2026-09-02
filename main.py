#!/usr/bin/env python3
"""
MehdiLabs Cours — Application de gestion de cours avec IA (Version Windows).
Point d'entrée principal (tkinter).
"""

import sys
import os
from pathlib import Path

import tkinter as tk

# --- FIX: Boutons blancs illisibles (macOS/Windows dark mode) ---
class FlatButton(tk.Label):
    def __init__(self, master=None, **kw):
        self.command = kw.pop('command', None)
        self.active_bg = kw.pop('activebackground', kw.get('bg', '#333333'))
        self.active_fg = kw.pop('activeforeground', kw.get('fg', 'white'))
        self.default_bg = kw.get('bg', '#333333')
        self.default_fg = kw.get('fg', 'white')
        
        for k in ['bd', 'relief', 'highlightthickness', 'highlightbackground', 'highlightcolor', 'state', 'disabledforeground']:
            kw.pop(k, None)
            
        kw['bd'] = 0
        super().__init__(master, **kw)
        
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)

    def on_enter(self, e):
        self.config(bg=self.active_bg, fg=self.active_fg)

    def on_leave(self, e):
        self.config(bg=self.default_bg, fg=self.default_fg)

    def on_click(self, e):
        if self.command:
            self.command()

tk.Button = FlatButton
# ----------------------------------------------------------------

from app.main_window import MainWindow


def get_app_dir() -> str:
    """Retourne le répertoire de l'application."""
    return str(Path(__file__).parent.resolve())


def get_cours_dir() -> str:
    """Retourne le répertoire des cours."""
    return str(Path(__file__).parent.resolve() / "cours")


def main():
    app_dir = get_app_dir()
    cours_dir = get_cours_dir()
    os.makedirs(cours_dir, exist_ok=True)

    # Initialize Tkinter
    root = MainWindow(app_dir, cours_dir)
    
    # Run application
    root.mainloop()


if __name__ == "__main__":
    main()
