#!/usr/bin/env python3
"""
MehdiLabs Cours — Application de gestion de cours avec IA (Version Windows).
Point d'entrée principal (tkinter).
"""

import sys
import os
from pathlib import Path

import tkinter as tk
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
