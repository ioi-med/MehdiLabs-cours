"""
Editor — Éditeur Markdown avec preview (tkinter, version Windows).
Split view avec barre d'outils de formatage, sauvegarde automatique, 
compteur de mots, recherche, et export PDF.
"""

import os
import platform
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from app.markdown_preview import MarkdownPreview
from app.markdown_parser import markdown_to_html


class Editor(ttk.Frame):
    """Éditeur Markdown avec preview, toolbar, auto-save et nouvelles fonctionnalités."""

    def __init__(self, parent, settings=None):
        super().__init__(parent)
        self.settings = settings
        self.current_file = None
        self._modified = False
        self.content_changed_callback = None
        self._auto_save_after_id = None
        
        self.focus_mode = False
        self.typewriter_mode = False
        self.scratchpad_visible = False
        
        self._setup_ui()
        self._setup_highlighter()

    def set_content_changed_callback(self, callback):
        self.content_changed_callback = callback

    def _setup_ui(self):
        style = ttk.Style()
        style.configure("Editor.TFrame", background="#1E1E1E")
        self.configure(style="Editor.TFrame")
        
        # --- Placeholder when no file is open ---
        self.placeholder_frame = ttk.Frame(self, style="Editor.TFrame")
        self.placeholder_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        lbl_icon = tk.Label(self.placeholder_frame, text="📄", font=("Segoe UI", 48), bg="#1E1E1E", fg="#666666")
        lbl_icon.pack()
        lbl_text = tk.Label(self.placeholder_frame, text="Sélectionnez un fichier pour l'éditer", font=("Segoe UI", 16), bg="#1E1E1E", fg="#999999")
        lbl_text.pack(pady=10)
        
        # --- Main Editor Area (Hidden initially) ---
        self.editor_frame = ttk.Frame(self, style="Editor.TFrame")
        
        # Top bar (tabs + toolbar)
        top_bar = ttk.Frame(self.editor_frame, style="Editor.TFrame")
        top_bar.pack(fill=tk.X)
        
        # Tab
        tab_frame = tk.Frame(top_bar, bg="#252526")
        tab_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        self.tab_label = tk.Label(tab_frame, text="  nom_fichier.md  ", bg="#1E1E1E", fg="#0A84FF", font=("Segoe UI", 12))
        self.tab_label.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))
        
        btn_close = tk.Button(tab_frame, text="✕", bg="#1E1E1E", fg="#858585", bd=0, activebackground="#1E1E1E", activeforeground="#FF453A", cursor="hand2", command=self.close_file)
        btn_close.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 10))
        
        # Save indicator
        self.save_indicator = tk.Label(top_bar, text="✓ Sauvegardé", bg="#1E1E1E", fg="#32D74B", font=("Segoe UI", 11))
        self.save_indicator.pack(side=tk.LEFT, padx=15)
        
        # Toolbar
        toolbar = ttk.Frame(top_bar, style="Editor.TFrame")
        toolbar.pack(side=tk.RIGHT, padx=10, pady=5)
        
        tools = [
            ("B", self._insert_bold, "Gras (Ctrl+B)"),
            ("I", self._insert_italic, "Italique (Ctrl+I)"),
            ("H", self._insert_heading, "Titre"),
            ("≡", self._insert_list, "Liste"),
            ("</>", self._insert_code, "Code"),
            ("🔗", self._insert_link, "Lien"),
            ("🖼️", self._insert_image, "Image"),
            ("📊", self._insert_table, "Insérer un tableau"),
            ("|", None, ""),
            ("🔍", self._show_search, "Rechercher (Ctrl+F)"),
            ("📑 Plan", self._toggle_outline, "Afficher/Masquer le Plan"),
            ("📝 Notes", self._toggle_scratchpad, "Bloc-notes rapide (Scratchpad)"),
            ("⌨️ Zen", self._toggle_typewriter, "Mode Machine à écrire"),
            ("📄 PDF", self._export_pdf, "Exporter en PDF"),
            ("🌐 HTML", self._export_html, "Exporter en HTML"),
            ("👁️ Focus", self._toggle_focus, "Mode Focus"),
            ("🔊 Lire", self._read_aloud, "Lire le cours à voix haute (Windows SAPI)"),
            ("🌐", self._open_browser_preview, "Ouvrir dans le navigateur"),
        ]
        
        for text, cmd, tip in tools:
            if text == "|":
                tk.Label(toolbar, text=" | ", bg="#1E1E1E", fg="#444444").pack(side=tk.LEFT)
                continue
            btn = tk.Button(toolbar, text=text, bg="#1E1E1E", fg="#858585", bd=0, font=("Segoe UI", 12, "bold"), cursor="hand2", command=cmd)
            btn.pack(side=tk.LEFT, padx=2)
            
        # Search Bar (Hidden initially)
        self.search_frame = tk.Frame(self.editor_frame, bg="#252526", pady=5, padx=10)
        tk.Label(self.search_frame, text="🔍 Rechercher :", bg="#252526", fg="#FFFFFF", font=("Segoe UI", 11)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(self.search_frame, textvariable=self.search_var, bg="#333333", fg="#FFFFFF", insertbackground="#FFFFFF", width=20)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind("<Return>", lambda e: self._find_next())
        
        tk.Button(self.search_frame, text="Suivant", bg="#333333", fg="#E0E0E0", bd=0, cursor="hand2", command=self._find_next).pack(side=tk.LEFT, padx=2)
        tk.Label(self.search_frame, text=" Remplacer par :", bg="#252526", fg="#FFFFFF", font=("Segoe UI", 11)).pack(side=tk.LEFT)
        self.replace_var = tk.StringVar()
        self.replace_entry = tk.Entry(self.search_frame, textvariable=self.replace_var, bg="#333333", fg="#FFFFFF", insertbackground="#FFFFFF", width=20)
        self.replace_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Button(self.search_frame, text="Remplacer", bg="#333333", fg="#E0E0E0", bd=0, cursor="hand2", command=self._replace_current).pack(side=tk.LEFT, padx=2)
        tk.Button(self.search_frame, text="Tout remplacer", bg="#333333", fg="#E0E0E0", bd=0, cursor="hand2", command=self._replace_all).pack(side=tk.LEFT, padx=2)
        tk.Button(self.search_frame, text="✕", bg="#252526", fg="#FF453A", bd=0, cursor="hand2", command=self._hide_search).pack(side=tk.RIGHT, padx=5)
            
        # Splitter (PanedWindow)
        self.paned_window = ttk.PanedWindow(self.editor_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left pane: Text Editor container
        editor_container = ttk.Frame(self.paned_window, style="Editor.TFrame")
        
        # Outline (Hidden by default)
        self.outline_frame = tk.Frame(editor_container, bg="#252526", width=200)
        self.outline_list = tk.Listbox(self.outline_frame, bg="#252526", fg="#E0E0E0", bd=0, highlightthickness=0, font=("Segoe UI", 12), selectbackground="#0A84FF")
        self.outline_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.outline_list.bind("<<ListboxSelect>>", self._on_outline_click)
        self.outline_visible = False
        
        self.text_edit = tk.Text(editor_container, bg="#1E1E1E", fg="#FFFFFF", insertbackground="#FFFFFF", 
                                bd=0, highlightthickness=0, font=("Consolas", 14), wrap=tk.WORD,
                                padx=10, pady=10, undo=True)
        self.text_edit.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scroll_edit = ttk.Scrollbar(editor_container, command=self.text_edit.yview)
        scroll_edit.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_edit.configure(yscrollcommand=scroll_edit.set)
        
        self.paned_window.add(editor_container, weight=1)
        
        # Right pane: Preview
        self.preview = MarkdownPreview(self.paned_window)
        self.paned_window.add(self.preview, weight=1)
        
        # Scratchpad container (Hidden by default)
        self.scratchpad_frame = tk.Frame(self.editor_frame, bg="#252526", width=220)
        scratchpad_top = tk.Frame(self.scratchpad_frame, bg="#252526", pady=5, padx=8)
        scratchpad_top.pack(fill=tk.X)
        tk.Label(scratchpad_top, text="📝 Bloc-notes rapide", bg="#252526", fg="#FFD60A", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        tk.Button(scratchpad_top, text="✕", bg="#252526", fg="#FF453A", bd=0, cursor="hand2", command=self._toggle_scratchpad).pack(side=tk.RIGHT)
        
        self.scratchpad_text = tk.Text(self.scratchpad_frame, bg="#1E1E1E", fg="#FFFFFF", insertbackground="#FFFFFF",
                                      bd=0, highlightthickness=0, font=("Consolas", 12), wrap=tk.WORD, padx=8, pady=8)
        self.scratchpad_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        
        # Bottom bar: Word Counter
        bottom_bar = tk.Frame(self.editor_frame, bg="#252526", height=24)
        bottom_bar.pack(fill=tk.X, side=tk.BOTTOM)
        bottom_bar.pack_propagate(False)
        self.lbl_stats = tk.Label(bottom_bar, text="Mots: 0 • Caractères: 0 • Lignes: 0", bg="#252526", fg="#999999", font=("Segoe UI", 11))
        self.lbl_stats.pack(side=tk.RIGHT, padx=10)
        
        # Bindings (Ctrl for Windows)
        self.text_edit.bind("<<Modified>>", self._on_text_changed)
        self.text_edit.bind("<Control-s>", lambda e: self.save_file())
        self.text_edit.bind("<Control-b>", lambda e: self._insert_bold())
        self.text_edit.bind("<Control-i>", lambda e: self._insert_italic())
        self.text_edit.bind("<Control-f>", lambda e: self._show_search())
        self.text_edit.bind("<KeyRelease>", self._on_key_release)

    def _setup_highlighter(self):
        """Configure tags for very basic syntax highlighting and search."""
        self.text_edit.tag_configure("md_heading", foreground="#0A84FF", font=("Consolas", 14, "bold"))
        self.text_edit.tag_configure("md_bold", foreground="#FFFFFF", font=("Consolas", 14, "bold"))
        self.text_edit.tag_configure("md_italic", foreground="#E0E0E0", font=("Consolas", 14, "italic"))
        self.text_edit.tag_configure("md_code", foreground="#5AC8FA")
        self.text_edit.tag_configure("md_link", foreground="#32D74B", underline=True)
        
        self.text_edit.tag_configure("search_match", background="#0A84FF", foreground="white")

    # --- Search & Replace ---
    def _show_search(self):
        self.search_frame.pack(fill=tk.X, before=self.paned_window)
        self.search_entry.focus_set()
        
    def _hide_search(self):
        self.search_frame.pack_forget()
        self.text_edit.tag_remove("search_match", "1.0", tk.END)
        self.text_edit.focus_set()

    def _find_next(self):
        self.text_edit.tag_remove("search_match", "1.0", tk.END)
        query = self.search_var.get()
        if not query:
            return
            
        start_pos = self.text_edit.index(tk.INSERT)
        pos = self.text_edit.search(query, start_pos, stopindex=tk.END, nocase=True)
        if not pos:
            # Wrap around
            pos = self.text_edit.search(query, "1.0", stopindex=start_pos, nocase=True)
            
        if pos:
            end_pos = f"{pos} + {len(query)} chars"
            self.text_edit.tag_add("search_match", pos, end_pos)
            self.text_edit.mark_set(tk.INSERT, end_pos)
            self.text_edit.see(pos)
        else:
            messagebox.showinfo("Recherche", "Aucun résultat trouvé.")

    def _replace_current(self):
        query = self.search_var.get()
        replacement = self.replace_var.get()
        if not query:
            return
            
        ranges = self.text_edit.tag_ranges("search_match")
        if ranges:
            self.text_edit.delete(ranges[0], ranges[1])
            self.text_edit.insert(ranges[0], replacement)
            self._find_next()
        else:
            self._find_next()
            ranges = self.text_edit.tag_ranges("search_match")
            if ranges:
                self.text_edit.delete(ranges[0], ranges[1])
                self.text_edit.insert(ranges[0], replacement)
                self._find_next()

    def _replace_all(self):
        query = self.search_var.get()
        replacement = self.replace_var.get()
        if not query:
            return
            
        count = 0
        pos = "1.0"
        while True:
            pos = self.text_edit.search(query, pos, stopindex=tk.END, nocase=True)
            if not pos:
                break
            end_pos = f"{pos} + {len(query)} chars"
            self.text_edit.delete(pos, end_pos)
            self.text_edit.insert(pos, replacement)
            pos = f"{pos} + {len(replacement)} chars"
            count += 1
            
        messagebox.showinfo("Remplacer", f"{count} occurrences remplacées.")

    # --- Outline ---
    def _toggle_outline(self):
        if self.outline_visible:
            self.outline_frame.pack_forget()
            self.outline_visible = False
        else:
            self.outline_frame.pack(side=tk.LEFT, fill=tk.Y, before=self.text_edit)
            self.outline_visible = True
            self._update_outline()
            
    def _update_outline(self):
        if not self.outline_visible: return
        self.outline_list.delete(0, tk.END)
        content = self.text_edit.get("1.0", tk.END)
        self.outline_lines = []
        for i, line in enumerate(content.split('\n')):
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                title = line.strip("# ").strip()
                indent = "  " * (level - 1)
                self.outline_list.insert(tk.END, f"{indent}{title}")
                self.outline_lines.append(i + 1)
                
    def _on_outline_click(self, event):
        selection = self.outline_list.curselection()
        if selection:
            line_idx = self.outline_lines[selection[0]]
            self.text_edit.see(f"{line_idx}.0")
            self.text_edit.mark_set(tk.INSERT, f"{line_idx}.0")
            self.text_edit.focus_set()

    # --- Scratchpad ---
    def _toggle_scratchpad(self):
        if self.scratchpad_visible:
            self.scratchpad_frame.pack_forget()
            self.scratchpad_visible = False
        else:
            self.scratchpad_frame.pack(side=tk.RIGHT, fill=tk.Y, before=self.paned_window)
            self.scratchpad_visible = True

    # --- Typewriter & Snippets ---
    def _toggle_typewriter(self):
        self.typewriter_mode = not self.typewriter_mode
        if self.typewriter_mode:
            self._center_cursor()

    def _center_cursor(self):
        if self.typewriter_mode:
            self.text_edit.see(tk.INSERT)
            # Center current line by scrolling
            try:
                line = int(self.text_edit.index(tk.INSERT).split('.')[0])
                total_lines = int(self.text_edit.index('end-1c').split('.')[0])
                fraction = max(0.0, min(1.0, (line - 10) / max(total_lines, 1)))
                self.text_edit.yview_moveto(fraction)
            except Exception:
                pass

    def _on_key_release(self, event):
        self._update_stats()
        if self.typewriter_mode:
            self._center_cursor()
        
        # Snippets check on Space or Return
        if event.keysym in ("space", "Return"):
            self._check_snippets()

    def _check_snippets(self):
        snippets = {
            "/def": "**Définition :** ",
            "/ex": "**Exemple :** ",
            "/rem": "> **Remarque :** ",
            "/todo": "- [ ] ",
            "/date": f"_{__import__('datetime').datetime.now().strftime('%d/%m/%Y')}_ ",
        }
        curr = self.text_edit.index(tk.INSERT)
        line_start = f"{curr} linestart"
        line_text = self.text_edit.get(line_start, curr)
        for key, val in snippets.items():
            if key in line_text:
                idx = line_text.rfind(key)
                start_replace = f"{line_start} + {idx} chars"
                end_replace = f"{start_replace} + {len(key)} chars"
                self.text_edit.delete(start_replace, end_replace)
                self.text_edit.insert(start_replace, val)
                break

    # --- Mode Focus ---
    def _toggle_focus(self):
        self.focus_mode = not self.focus_mode
        # In a real focus mode we'd hide sidebar too, but this requires coordination with main_window.
        # Here we maximize editor area by hiding the preview.
        if self.focus_mode:
            self.paned_window.remove(self.preview)
        else:
            self.paned_window.add(self.preview, weight=1)

    # --- Stats ---
    def _update_stats(self, event=None):
        content = self.text_edit.get("1.0", "end-1c")
        chars = len(content)
        words = len([w for w in content.split() if w.strip()])
        lines = content.count("\n") + 1 if chars > 0 else 0
        self.lbl_stats.config(text=f"Mots: {words} • Caractères: {chars} • Lignes: {lines}")

    # --- Export PDF ---
    def _export_pdf(self):
        if not self.current_file:
            return
        content = self.text_edit.get("1.0", "end-1c")
        html = markdown_to_html(content)
        
        # Inject print script so it immediately opens print dialog (Save as PDF)
        html += "<script>window.onload = function() { window.print(); }</script>"
        self.preview.open_in_browser(html)

    # --- Core Editor Functions ---
    def open_file(self, filepath: str):
        if self.current_file == filepath:
            return

        if self._modified:
            self.save_file()

        if not os.path.exists(filepath):
            return

        ext = os.path.splitext(filepath)[1].lower()
        text_extensions = {".md", ".txt", ".json", ".py", ".csv", ".html", ".css", ".js"}

        if ext not in text_extensions:
            self._open_with_system(filepath)
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(filepath, "r", encoding="latin-1") as f:
                    content = f.read()
            except Exception as e:
                messagebox.showwarning("Erreur", f"Impossible de lire le fichier:\n{e}")
                return
        except Exception as e:
            messagebox.showwarning("Erreur", f"Impossible de lire le fichier:\n{e}")
            return

        self.current_file = filepath
        if self.settings:
            self.settings.set_last_opened_file(filepath)
        
        # Prevent <<Modified>> event during loading
        self.text_edit.edit_modified(False)
        self.text_edit.delete("1.0", tk.END)
        self.text_edit.insert(tk.END, content)
        self.text_edit.edit_modified(False)
        
        self._modified = False
        self._update_save_indicator()
        self._update_stats()

        # Update tab
        self.tab_label.config(text=f"  {os.path.basename(filepath)}  ")

        # Show editor
        self.placeholder_frame.place_forget()
        self.editor_frame.pack(fill=tk.BOTH, expand=True)

        # Update preview if markdown
        if ext == ".md":
            self.preview.update_content(content)

    def _open_with_system(self, filepath: str):
        """Ouvre un fichier avec l'application par défaut de Windows."""
        try:
            os.startfile(filepath)
        except Exception:
            messagebox.showinfo("Fichier non supporté", "Le fichier sera ouvert avec l'application par défaut.")

    def close_file(self):
        if self._modified:
            reply = messagebox.askyesnocancel("Sauvegarder ?", "Le fichier a été modifié. Sauvegarder avant de fermer ?")
            if reply is True:
                self.save_file()
            elif reply is None:
                return

        self.current_file = None
        self._modified = False
        self.text_edit.delete("1.0", tk.END)
        self.preview.update_content("")
        
        self.editor_frame.pack_forget()
        self.placeholder_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def save_file(self):
        if not self.current_file:
            return

        try:
            content = self.text_edit.get("1.0", "end-1c")
            
            # --- Auto-Backup (Historique) ---
            if os.path.exists(self.current_file):
                import time
                backup_dir = os.path.join(os.path.dirname(self.current_file), ".backups")
                os.makedirs(backup_dir, exist_ok=True)
                
                # Check last modified time, only backup if it's older than 1 minute to avoid spam
                mtime = os.path.getmtime(self.current_file)
                if time.time() - mtime > 60:
                    base_name = os.path.basename(self.current_file)
                    backup_name = f"{int(mtime)}_{base_name}"
                    import shutil
                    shutil.copy2(self.current_file, os.path.join(backup_dir, backup_name))
            
            # --- Normal Save ---
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(content)
                
            self._modified = False
            self.text_edit.edit_modified(False)
            self._update_save_indicator()
        except Exception as e:
            messagebox.showwarning("Erreur", f"Impossible de sauvegarder:\n{e}")

    def _auto_save(self):
        if self.current_file and self._modified:
            self.save_file()
        self._auto_save_after_id = None

    def _on_text_changed(self, event=None):
        if not self.text_edit.edit_modified():
            return
            
        self._modified = True
        self._update_save_indicator()
        
        if self.content_changed_callback:
            self.content_changed_callback()

        # Update preview with slight delay
        if self.current_file and self.current_file.endswith(".md"):
            content = self.text_edit.get("1.0", "end-1c")
            self.preview.update_content(content)
            self._update_stats()
            self._update_outline()
            
        # Schedule auto-save
        if self._auto_save_after_id:
            self.after_cancel(self._auto_save_after_id)
        self._auto_save_after_id = self.after(30000, self._auto_save) # 30s
            
        # Reset modified flag to catch next change
        self.text_edit.edit_modified(False)

    def _update_save_indicator(self):
        if self._modified:
            self.save_indicator.config(text="● Modifié", fg="#FFD60A")
            if self.current_file:
                self.tab_label.config(text=f"  ● {os.path.basename(self.current_file)}  ")
        else:
            self.save_indicator.config(text="✓ Sauvegardé", fg="#32D74B")
            if self.current_file:
                self.tab_label.config(text=f"  {os.path.basename(self.current_file)}  ")

    # --- Format Tools ---
    def _wrap_selection(self, before: str, after: str):
        try:
            start = self.text_edit.index(tk.SEL_FIRST)
            end = self.text_edit.index(tk.SEL_LAST)
            text = self.text_edit.get(start, end)
            self.text_edit.delete(start, end)
            self.text_edit.insert(start, f"{before}{text}{after}")
        except tk.TclError:
            # No selection
            insert_pos = self.text_edit.index(tk.INSERT)
            self.text_edit.insert(insert_pos, f"{before}{after}")
            # Move cursor between tags
            new_pos = f"{insert_pos} + {len(before)} chars"
            self.text_edit.mark_set(tk.INSERT, new_pos)
            
        self.text_edit.focus_set()
        
    def _insert_bold(self):
        self._wrap_selection("**", "**")

    def _insert_italic(self):
        self._wrap_selection("*", "*")

    def _insert_heading(self):
        pos = self.text_edit.index(tk.INSERT)
        line_start = f"{pos} linestart"
        self.text_edit.insert(line_start, "## ")

    def _insert_list(self):
        pos = self.text_edit.index(tk.INSERT)
        line_start = f"{pos} linestart"
        self.text_edit.insert(line_start, "- ")

    def _insert_code(self):
        try:
            start = self.text_edit.index(tk.SEL_FIRST)
            end = self.text_edit.index(tk.SEL_LAST)
            text = self.text_edit.get(start, end)
            if "\n" in text:
                self._wrap_selection("```\n", "\n```")
            else:
                self._wrap_selection("`", "`")
        except tk.TclError:
            self._wrap_selection("```\n\n```", "")
            pos = self.text_edit.index(tk.INSERT)
            self.text_edit.mark_set(tk.INSERT, f"{pos} - 4 chars")
            self.text_edit.focus_set()

    def _insert_link(self):
        self._wrap_selection("[", "](url)")

    def _insert_image(self):
        filepath = filedialog.askopenfilename(
            title="Sélectionner une image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.svg *.webp")]
        )
        if filepath:
            self.text_edit.insert(tk.INSERT, f"![image]({filepath})")

    def _insert_table(self):
        table_md = "\n| Colonne 1 | Colonne 2 | Colonne 3 |\n| :--- | :---: | ---: |\n| Valeur | Valeur | Valeur |\n| Valeur | Valeur | Valeur |\n"
        self.text_edit.insert(tk.INSERT, table_md)
        
    def _export_html(self):
        if not self.current_file: return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML files", "*.html")],
            initialfile=os.path.basename(self.current_file).replace(".md", ".html")
        )
        if filepath:
            content = self.text_edit.get("1.0", "end-1c")
            html_body = markdown_to_html(content)
            
            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: "Segoe UI", sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 40px; }}
                    h1, h2, h3 {{ color: #0A84FF; }}
                    code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 4px; }}
                    pre {{ background: #f5f5f5; padding: 16px; border-radius: 8px; overflow-x: auto; }}
                    blockquote {{ border-left: 4px solid #0A84FF; padding-left: 16px; color: #666; }}
                    table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px 12px; }}
                    th {{ background: #f8f8f8; }}
                </style>
            </head>
            <body>
                {html_body}
            </body>
            </html>
            """
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(full_html)
                messagebox.showinfo("Export réussi", "Le fichier HTML a été généré avec succès.")
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
                
    def _read_aloud(self):
        """Lecture à voix haute via Windows SAPI (synthèse vocale)."""
        try:
            # Read selection or entire text
            try:
                start = self.text_edit.index(tk.SEL_FIRST)
                end = self.text_edit.index(tk.SEL_LAST)
                text = self.text_edit.get(start, end)
            except tk.TclError:
                text = self.text_edit.get("1.0", "end-1c")
                
            if not text.strip(): return
            
            # Clean markdown symbols for better speech
            clean_text = text.replace("#", "").replace("*", "").replace("`", "").replace("_", "")
            # Escape single quotes for PowerShell
            clean_text = clean_text.replace("'", "''")
            
            import threading
            def speak():
                try:
                    # Use PowerShell with Windows SAPI
                    ps_cmd = f"Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak('{clean_text}')"
                    subprocess.Popen(["powershell", "-Command", ps_cmd], 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass
            threading.Thread(target=speak, daemon=True).start()
        except Exception:
            pass
            
    def _open_browser_preview(self):
        if not self.current_file or not self.current_file.endswith(".md"):
            return
        content = self.text_edit.get("1.0", "end-1c")
        html = markdown_to_html(content)
        self.preview.open_in_browser(html)
