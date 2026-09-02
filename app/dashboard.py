"""
Dashboard — Page d'accueil avec les statistiques des cours.
"""

import os
import tkinter as tk
from tkinter import ttk
from datetime import datetime

class Dashboard(ttk.Frame):
    """Dashboard affichant les statistiques globales des cours."""

    def __init__(self, parent, cours_dir: str):
        super().__init__(parent)
        self.cours_dir = cours_dir
        self.start_time = datetime.now()
        
        style = ttk.Style()
        style.configure("Dashboard.TFrame", background="#1E1E1E")
        self.configure(style="Dashboard.TFrame")
        
        self._setup_ui()
        self.refresh_stats()

    def _setup_ui(self):
        # Container with max width
        container = tk.Frame(self, bg="#1E1E1E")
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER, relwidth=0.8, relheight=0.8)
        
        # Title
        title_frame = tk.Frame(container, bg="#1E1E1E")
        title_frame.pack(fill=tk.X, pady=(0, 30))
        tk.Label(title_frame, text="👋 Bienvenue sur MehdiLabs Cours", bg="#1E1E1E", fg="#FFFFFF", font=("Segoe UI", 28, "bold")).pack(anchor="w")
        tk.Label(title_frame, text="Voici un résumé de tes cours actuels.", bg="#1E1E1E", fg="#999999", font=("Segoe UI", 16)).pack(anchor="w", pady=(5, 0))
        
        # Stats Grid
        self.grid_frame = tk.Frame(container, bg="#1E1E1E")
        self.grid_frame.pack(fill=tk.X, pady=20)
        
        # Columns configuration
        for i in range(4):
            self.grid_frame.grid_columnconfigure(i, weight=1, pad=10)
            
        self.stat_files = self._create_stat_card("📄 Cours", "0", 0, 0, "#0A84FF")
        self.stat_dirs = self._create_stat_card("📁 Matières", "0", 0, 1, "#32D74B")
        self.stat_words = self._create_stat_card("✍️ Mots totaux", "0", 0, 2, "#FF9F0A")
        self.stat_time = self._create_stat_card("⏳ Session", "0m", 0, 3, "#BF5AF2")
        
        # Split bottom area into 2 columns
        bottom_frame = tk.Frame(container, bg="#1E1E1E")
        bottom_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        
        # Recent files list (Left)
        recent_frame = tk.Frame(bottom_frame, bg="#1E1E1E")
        recent_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        tk.Label(recent_frame, text="🕒 Récemment modifiés", bg="#1E1E1E", fg="#FFFFFF", font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(0, 15))
        
        self.recent_list = tk.Frame(recent_frame, bg="#252526", bd=1, relief=tk.SOLID, highlightbackground="#3C3C3C", highlightthickness=1)
        self.recent_list.pack(fill=tk.BOTH, expand=True)
        
        # Todo list (Right)
        todo_frame = tk.Frame(bottom_frame, bg="#1E1E1E")
        todo_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        tk.Label(todo_frame, text="☑️ Tâches en attente", bg="#1E1E1E", fg="#FFFFFF", font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(0, 15))
        
        # Scrollable todo list
        todo_canvas = tk.Canvas(todo_frame, bg="#252526", highlightthickness=1, highlightbackground="#3C3C3C")
        todo_scroll = ttk.Scrollbar(todo_frame, orient="vertical", command=todo_canvas.yview)
        
        self.todo_list = tk.Frame(todo_canvas, bg="#252526")
        self.todo_list.bind("<Configure>", lambda e: todo_canvas.configure(scrollregion=todo_canvas.bbox("all")))
        
        todo_canvas.create_window((0, 0), window=self.todo_list, anchor="nw")
        todo_canvas.configure(yscrollcommand=todo_scroll.set)
        
        todo_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        todo_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _create_stat_card(self, title, value, row, col, color):
        card = tk.Frame(self.grid_frame, bg="#252526", bd=1, relief=tk.SOLID, highlightbackground="#3C3C3C", highlightthickness=1, padx=20, pady=20)
        card.grid(row=row, column=col, sticky="nsew")
        
        tk.Label(card, text=title, bg="#252526", fg="#999999", font=("Segoe UI", 14)).pack(anchor="w")
        val_lbl = tk.Label(card, text=value, bg="#252526", fg=color, font=("Segoe UI", 32, "bold"))
        val_lbl.pack(anchor="w", pady=(10, 0))
        
        return val_lbl

    def refresh_stats(self):
        total_files = 0
        total_dirs = 0
        total_words = 0
        
        all_files = []
        all_todos = []

        for root, dirs, files in os.walk(self.cours_dir):
            if ".chat_history" in root:
                continue
                
            total_dirs += len(dirs)
            
            for file in files:
                if file.startswith("."): continue
                total_files += 1
                
                filepath = os.path.join(root, file)
                
                if file.endswith(".md"):
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                            total_words += len(content.split())
                            
                            # Extract TODOs
                            for line in content.split('\n'):
                                line = line.strip()
                                if line.startswith("- [ ]") or line.startswith("* [ ]"):
                                    all_todos.append((filepath, line[5:].strip()))
                    except:
                        pass
                
                # Get modified time
                mtime = os.path.getmtime(filepath)
                all_files.append((filepath, mtime))
                
        self.stat_files.config(text=str(total_files))
        self.stat_dirs.config(text=str(total_dirs))
        self.stat_words.config(text=str(total_words))
        
        delta = datetime.now() - self.start_time
        minutes = int(delta.total_seconds() / 60)
        self.stat_time.config(text=f"{minutes}m")
        
        # Sort by mtime descending
        all_files.sort(key=lambda x: x[1], reverse=True)
        recent = all_files[:5]
        
        # Clear recent list
        for widget in self.recent_list.winfo_children():
            widget.destroy()
            
        if not recent:
            tk.Label(self.recent_list, text="Aucun fichier", bg="#252526", fg="#858585", font=("Segoe UI", 14), pady=20).pack()
        else:
            for filepath, mtime in recent:
                rel_path = os.path.relpath(filepath, self.cours_dir)
                date_str = datetime.fromtimestamp(mtime).strftime("%d/%m/%Y %H:%M")
                
                row = tk.Frame(self.recent_list, bg="#252526")
                row.pack(fill=tk.X, padx=15, pady=10)
                
                tk.Label(row, text="📄", bg="#252526", fg="#0A84FF", font=("Segoe UI", 14)).pack(side=tk.LEFT)
                tk.Label(row, text=rel_path, bg="#252526", fg="#E0E0E0", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT, padx=10)
                tk.Label(row, text=date_str, bg="#252526", fg="#858585", font=("Segoe UI", 12)).pack(side=tk.RIGHT)
                
                # Separator
                tk.Frame(self.recent_list, bg="#3C3C3C", height=1).pack(fill=tk.X)
                
        # Update TODOs
        for widget in self.todo_list.winfo_children():
            widget.destroy()
            
        if not all_todos:
            tk.Label(self.todo_list, text="Aucune tâche en attente ! 🎉", bg="#252526", fg="#32D74B", font=("Segoe UI", 14), pady=20).pack(fill=tk.X)
        else:
            for filepath, task in all_todos:
                row = tk.Frame(self.todo_list, bg="#252526")
                row.pack(fill=tk.X, padx=15, pady=8)
                
                tk.Label(row, text="☐", bg="#252526", fg="#FF9F0A", font=("Segoe UI", 16)).pack(side=tk.LEFT)
                
                task_lbl = tk.Label(row, text=task, bg="#252526", fg="#E0E0E0", font=("Segoe UI", 13), wraplength=300, justify=tk.LEFT)
                task_lbl.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
                
                # Context (filename)
                rel_path = os.path.basename(filepath)
                tk.Label(row, text=rel_path, bg="#252526", fg="#858585", font=("Segoe UI", 10)).pack(side=tk.RIGHT)
                
                tk.Frame(self.todo_list, bg="#3C3C3C", height=1).pack(fill=tk.X)
