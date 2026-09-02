"""
File Manager — Gestionnaire de fichiers pour organiser les cours.
Affiche un arbre de fichiers avec actions CRUD (tkinter, version Windows).
Gère les favoris/récents et les modèles de cours.
"""

import os
import shutil
import platform
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog


class FileManager(ttk.Frame):
    """Widget de gestion de fichiers avec arbre, actions, récents et templates."""

    # Templates de cours
    TEMPLATES = {
        "Vide": "# {title}\n\n",
        "Cours structuré": "# {title}\n\n## 1. Introduction\n\n## 2. Concepts clés\n- \n- \n\n## 3. Conclusion\n\n",
        "Fiche de révision": "# Fiche : {title}\n\n### Définitions\n- \n\n### Formules / Points clés\n- \n\n### À retenir\n- \n",
        "TD / Exercices": "# TD : {title}\n\n## Exercice 1\n**Énoncé :**\n\n**Brouillon :**\n\n**Correction :**\n",
    }

    def __init__(self, parent, cours_dir: str, settings=None):
        super().__init__(parent)
        self.cours_dir = cours_dir
        self.settings = settings
        os.makedirs(self.cours_dir, exist_ok=True)
        
        self.file_selected_callback = None
        self.file_double_clicked_callback = None
        
        # Soft delete directory
        self.trash_dir = os.path.join(self.cours_dir, ".trash")
        os.makedirs(self.trash_dir, exist_ok=True)
        
        # Sorting
        self.sort_var = tk.StringVar(value="Nom")

        self._setup_ui()
        self._refresh()

    def set_callbacks(self, on_selected=None, on_double_click=None):
        self.file_selected_callback = on_selected
        self.file_double_clicked_callback = on_double_click

    def _setup_ui(self):
        style = ttk.Style()
        style.configure("FileManager.TFrame", background="#1E1E1E")
        self.configure(style="FileManager.TFrame")
        
        # --- Toolbar ---
        toolbar = ttk.Frame(self, style="FileManager.TFrame")
        toolbar.pack(fill=tk.X, padx=8, pady=8)

        # Search bar
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self._on_search())
        search_entry = tk.Entry(toolbar, textvariable=self.search_var, bg="#333333", fg="#FFFFFF", 
                               insertbackground="#FFFFFF", bd=1, relief=tk.FLAT)
        search_entry.pack(fill=tk.X, pady=(0, 6))

        # Sort Dropdown
        sort_combo = ttk.Combobox(toolbar, textvariable=self.sort_var, values=["Nom", "Date", "Taille"], state="readonly", width=8, font=("Segoe UI", 11))
        sort_combo.pack(fill=tk.X, pady=(0, 6))
        sort_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh())

        # Action buttons
        btn_frame = ttk.Frame(toolbar, style="FileManager.TFrame")
        btn_frame.pack(fill=tk.X)

        self.btn_new_folder = tk.Button(btn_frame, text="📁 Dossier", bg="#333333", fg="#E0E0E0", 
                                       activebackground="#0058D0", activeforeground="#0A84FF", 
                                       bd=0, relief=tk.FLAT, cursor="hand2",
                                       command=self._create_folder)
        self.btn_new_folder.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_new_file = tk.Button(btn_frame, text="📄 Fichier", bg="#333333", fg="#E0E0E0", 
                                     activebackground="#0058D0", activeforeground="#0A84FF", 
                                     bd=0, relief=tk.FLAT, cursor="hand2",
                                     command=self._create_file)
        self.btn_new_file.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_refresh = tk.Button(btn_frame, text="🔄", bg="#333333", fg="#E0E0E0", 
                                    activebackground="#0058D0", activeforeground="#0A84FF", 
                                    bd=0, relief=tk.FLAT, cursor="hand2",
                                    command=self._refresh)
        self.btn_refresh.pack(side=tk.LEFT)

        # --- File tree ---
        tree_frame = ttk.Frame(self, style="FileManager.TFrame")
        tree_frame.pack(fill=tk.BOTH, expand=True)

        style.configure("Custom.Treeview", background="#1E1E1E", foreground="#FFFFFF", 
                        fieldbackground="#1E1E1E", borderwidth=0)
        style.map("Custom.Treeview", background=[("selected", "#0058D0")], foreground=[("selected", "#5E9DFF")])
        
        self.tree = ttk.Treeview(tree_frame, style="Custom.Treeview", show="tree")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<<TreeviewSelect>>", self._on_item_clicked)
        self.tree.bind("<Double-1>", self._on_item_double_clicked)
        self.tree.bind("<Button-3>", self._show_context_menu)  # Right-click on Windows

        # --- Info bar ---
        self.info_label = tk.Label(self, text="", bg="#1E1E1E", fg="#999999", anchor="w", font=("Segoe UI", 11))
        self.info_label.pack(fill=tk.X, padx=12, pady=6)

    def _populate_recent(self):
        """Ajoute la section des fichiers récents en haut de l'arbre."""
        if not self.settings:
            return
            
        recent = self.settings.get_recent_files()
        if not recent:
            return
            
        recent_node = self.tree.insert("", "end", text="⭐ Récents", values=("recent_root",))
        for filepath in recent:
            if os.path.exists(filepath):
                name = os.path.basename(filepath)
                self.tree.insert(recent_node, "end", text=f"📄 {name}", values=(filepath,))
        
        self.tree.item(recent_node, open=True)
        
        # Add a separator node (dummy)
        self.tree.insert("", "end", text="──────────", values=("separator",), tags=("separator",))
        self.tree.tag_configure("separator", foreground="#3C3C3C")

    def _populate_tree(self, parent_node, path):
        """Remplit récursivement l'arbre de fichiers."""
        try:
            items = os.listdir(path)
            
            # Application du tri
            sort_type = self.sort_var.get()
            if sort_type == "Nom":
                items.sort(key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
            elif sort_type == "Date":
                items.sort(key=lambda x: (not os.path.isdir(os.path.join(path, x)), -os.path.getmtime(os.path.join(path, x))))
            elif sort_type == "Taille":
                items.sort(key=lambda x: (not os.path.isdir(os.path.join(path, x)), -os.path.getsize(os.path.join(path, x))))
            
            for item in items:
                if item.startswith("."):
                    continue
                    
                full_path = os.path.join(path, item)
                is_dir = os.path.isdir(full_path)
                
                filter_text = self.search_var.get().lower()
                if filter_text and filter_text not in item.lower() and not is_dir:
                    continue
                
                icon = "📁 " if is_dir else "📄 "
                node = self.tree.insert(parent_node, "end", text=icon + item, values=(full_path,))
                
                if is_dir:
                    self._populate_tree(node, full_path)
                    if filter_text and not self.tree.get_children(node) and filter_text not in item.lower():
                        self.tree.delete(node)
                    elif filter_text:
                        self.tree.item(node, open=True)
        except PermissionError:
            pass

    def _refresh(self):
        """Rafraîchit l'arbre de fichiers."""
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # N'afficher les récents que s'il n'y a pas de recherche active
        if not self.search_var.get():
            self._populate_recent()
            
        self._populate_tree("", self.cours_dir)
        self._update_info()

    def _on_search(self):
        self._refresh()

    def _get_selected_path(self):
        selection = self.tree.selection()
        if not selection:
            return None
        val = self.tree.item(selection[0], "values")[0]
        if val in ("recent_root", "separator"):
            return None
        return val

    def _get_selected_dir(self):
        path = self._get_selected_path()
        if path is None:
            return self.cours_dir
        if os.path.isdir(path):
            return path
        return os.path.dirname(path)

    def _create_folder(self):
        parent_dir = self._get_selected_dir()
        name = simpledialog.askstring("Nouveau dossier", "Nom du dossier :", parent=self)
        if name and name.strip():
            new_path = os.path.join(parent_dir, name.strip())
            try:
                os.makedirs(new_path, exist_ok=True)
                self._refresh()
            except OSError as e:
                messagebox.showwarning("Erreur", f"Impossible de créer le dossier:\n{e}")

    def _create_file(self):
        parent_dir = self._get_selected_dir()
        
        # Fenêtre pour choisir le nom ET le template
        win = tk.Toplevel(self)
        win.title("Nouveau fichier")
        win.geometry("400x250")
        win.configure(bg="#1E1E1E")
        win.transient(self)
        win.grab_set()
        
        tk.Label(win, text="Nom du fichier :", bg="#1E1E1E", fg="#E0E0E0", font=("Segoe UI", 12)).pack(anchor="w", padx=20, pady=(20, 5))
        
        name_var = tk.StringVar(value="nouveau_cours")
        name_entry = tk.Entry(win, textvariable=name_var, bg="#333333", fg="#FFFFFF", insertbackground="#FFFFFF", width=30)
        name_entry.pack(fill=tk.X, padx=20)
        name_entry.selection_range(0, tk.END)
        name_entry.focus_set()
        
        tk.Label(win, text="Modèle (Template) :", bg="#1E1E1E", fg="#E0E0E0", font=("Segoe UI", 12)).pack(anchor="w", padx=20, pady=(15, 5))
        
        template_var = tk.StringVar(value="Vide")
        template_combo = ttk.Combobox(win, textvariable=template_var, values=list(self.TEMPLATES.keys()), state="readonly")
        template_combo.pack(fill=tk.X, padx=20)
        
        def on_create():
            name = name_var.get().strip()
            if not name: return
            if not name.endswith(".md"): name += ".md"
            
            new_path = os.path.join(parent_dir, name)
            template_name = template_var.get()
            content = self.TEMPLATES.get(template_name, self.TEMPLATES["Vide"])
            # Remplacer {title} par le nom sans extension
            content = content.replace("{title}", name[:-3].replace("_", " ").title())
            
            try:
                with open(new_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self._refresh()
                if self.file_double_clicked_callback:
                    self.file_double_clicked_callback(new_path)
            except OSError as e:
                messagebox.showwarning("Erreur", f"Impossible de créer le fichier:\n{e}")
            win.destroy()
            
        btn_frame = tk.Frame(win, bg="#1E1E1E")
        btn_frame.pack(fill=tk.X, pady=20, padx=20)
        tk.Button(btn_frame, text="Créer", bg="#0A84FF", fg="white", bd=0, cursor="hand2", padx=20, pady=5, command=on_create).pack(side=tk.RIGHT)
        tk.Button(btn_frame, text="Annuler", bg="#333333", fg="#E0E0E0", bd=0, cursor="hand2", padx=20, pady=5, command=win.destroy).pack(side=tk.RIGHT, padx=10)
        
        win.bind("<Return>", lambda e: on_create())

    def _rename_item(self):
        path = self._get_selected_path()
        if path is None:
            return

        old_name = os.path.basename(path)
        new_name = simpledialog.askstring("Renommer", "Nouveau nom :", parent=self, initialvalue=old_name)
        
        if new_name and new_name.strip() and new_name.strip() != old_name:
            new_path = os.path.join(os.path.dirname(path), new_name.strip())
            try:
                os.rename(path, new_path)
                self._refresh()
            except OSError as e:
                messagebox.showwarning("Erreur", f"Impossible de renommer:\n{e}")

    def _duplicate_item(self):
        path = self._get_selected_path()
        if not path or os.path.isdir(path):
            return
            
        base_dir = os.path.dirname(path)
        base_name, ext = os.path.splitext(os.path.basename(path))
        new_name = f"{base_name} (copie){ext}"
        new_path = os.path.join(base_dir, new_name)
        
        counter = 1
        while os.path.exists(new_path):
            new_name = f"{base_name} (copie {counter}){ext}"
            new_path = os.path.join(base_dir, new_name)
            counter += 1
            
        try:
            shutil.copy2(path, new_path)
            self._refresh()
        except OSError as e:
            messagebox.showwarning("Erreur", f"Impossible de dupliquer:\n{e}")

    def _delete_item(self):
        path = self._get_selected_path()
        if path is None:
            return

        name = os.path.basename(path)
        is_dir = os.path.isdir(path)
        type_name = "dossier" if is_dir else "fichier"

        if messagebox.askyesno("Placer dans la corbeille", f"Déplacer le {type_name} '{name}' vers la corbeille ?\n\n(Tu pourras le restaurer depuis le dossier caché .trash)"):
            try:
                dest = os.path.join(self.trash_dir, name)
                
                # S'il existe déjà un fichier du même nom dans la corbeille, on ajoute un timestamp
                if os.path.exists(dest):
                    import time
                    dest = os.path.join(self.trash_dir, f"{int(time.time())}_{name}")
                    
                shutil.move(path, dest)
                self._refresh()
            except OSError as e:
                messagebox.showwarning("Erreur", f"Impossible de déplacer vers la corbeille:\n{e}")

    def _open_in_explorer(self):
        path = self._get_selected_path()
        if path is None:
            path = self.cours_dir

        if os.path.isfile(path):
            path = os.path.dirname(path)

        # Windows: use explorer
        try:
            os.startfile(path)
        except Exception:
            try:
                subprocess.Popen(["explorer", path])
            except Exception:
                pass

    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            
        path = self._get_selected_path()
            
        menu = tk.Menu(self, tearoff=0, bg="#333333", fg="#E0E0E0")
        menu.add_command(label="📁 Nouveau dossier", command=self._create_folder)
        menu.add_command(label="📄 Nouveau fichier", command=self._create_file)
        
        if path:
            menu.add_separator()
            if not os.path.isdir(path):
                menu.add_command(label="📑 Dupliquer", command=self._duplicate_item)
            menu.add_command(label="✏️ Renommer", command=self._rename_item)
            menu.add_command(label="🗑️ Supprimer (Corbeille)", command=self._delete_item)
            
        menu.add_separator()
        menu.add_command(label="📂 Ouvrir dans l'explorateur", command=self._open_in_explorer)
        menu.add_command(label="🔄 Rafraîchir", command=self._refresh)
        
        menu.post(event.x_root, event.y_root)

    def _on_item_clicked(self, event):
        path = self._get_selected_path()
        if path and os.path.isfile(path) and self.file_selected_callback:
            self.file_selected_callback(path)

    def _on_item_double_clicked(self, event):
        path = self._get_selected_path()
        if path and os.path.isfile(path) and self.file_double_clicked_callback:
            if self.settings:
                self.settings.add_recent_file(path)
                self._refresh() # Update recent list
            self.file_double_clicked_callback(path)
            
    def _update_info(self):
        total_files = 0
        total_dirs = 0
        for root, dirs, files in os.walk(self.cours_dir):
            if ".chat_history" in root: continue
            total_dirs += len(dirs)
            total_files += len(files)
        self.info_label.config(text=f"📂 {total_dirs} dossiers • {total_files} fichiers")

    def get_file_count(self):
        total_files = 0
        total_dirs = 0
        for root, dirs, files in os.walk(self.cours_dir):
            if ".chat_history" in root: continue
            total_dirs += len(dirs)
            total_files += len(files)
        return total_dirs, total_files
