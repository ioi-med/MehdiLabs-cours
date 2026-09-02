"""
Chatbot — Interface de chatbot IA (tkinter, version Windows).
Gère l'historique et la communication avec les providers.
L'IA peut accéder aux cours du dossier cours/ pour contextualiser ses réponses.
"""

import json
import os
import uuid
from datetime import datetime
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from app.ai_providers import get_provider, AIProviderError, PROVIDERS
from app.settings import Settings
from app.markdown_parser import markdown_to_plain_formatted


class Chatbot(ttk.Frame):
    """Interface de chatbot IA complète avec historique et accès aux cours."""

    SYSTEM_PROMPT = (
        "Tu es un assistant pédagogique intelligent intégré dans l'application MehdiLabs Cours. "
        "Tu aides les étudiants à comprendre leurs cours, à résoudre des exercices, "
        "et à réviser efficacement. Réponds de manière claire, structurée et pédagogique. "
        "Utilise le Markdown pour formater tes réponses (titres, listes, code, etc.). "
        "Si on te demande un exercice, propose un exercice adapté au niveau et donne "
        "la correction détaillée. Réponds toujours en français."
    )

    # Boutons d'actions rapides avec leurs prompts
    QUICK_ACTIONS = [
        ("📝 Résume", "Fais un résumé clair et structuré de ce cours. Utilise des titres, des listes à puces et mets en gras les points clés."),
        ("❓ Quiz", "Crée un quiz de 5 questions (QCM) basé sur ce cours pour tester ma compréhension. Donne les réponses à la fin."),
        ("🎴 Flashcards", "Génère une série de 6 Flashcards (Question / Réponse) basées sur ce cours au format : \n**Q :** [Question]\n**R :** [Réponse concise]\n---"),
        ("🏗️ Plan de cours", "Propose un plan détaillé et structuré pour approfondir ce sujet ou créer un nouveau cours complet (Grand I, II, III avec sous-parties)."),
        ("🌐 Traduire en EN", "Traduis ce cours ou ce texte intégralement en anglais avec un vocabulaire académique précis."),
        ("💡 Explique", "Explique ce cours de manière simple, comme si tu l'expliquais à un débutant. Utilise des analogies et des exemples concrets."),
        ("📋 Fiche révision", "Crée une fiche de révision synthétique de ce cours avec : les définitions clés, les formules importantes, les points à retenir, et les pièges à éviter."),
    ]

    MAX_CONTEXT_CHARS = 6000  # Limite de caractères pour le contexte des cours

    def __init__(self, parent, settings: Settings, cours_dir: str):
        super().__init__(parent)
        self.settings = settings
        self.cours_dir = cours_dir
        self.chat_history_dir = os.path.join(cours_dir, ".chat_history")
        os.makedirs(self.chat_history_dir, exist_ok=True)

        self.current_conversation_id = None
        self.current_messages = []
        self._is_waiting = False
        self._attached_course = None  # Contenu du cours joint

        self._setup_ui()
        self._load_conversation_list()

    def _setup_ui(self):
        style = ttk.Style()
        style.configure("Chatbot.TFrame", background="#1E1E1E")
        self.configure(style="Chatbot.TFrame")

        # --- PanedWindow ---
        self.paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # --- Left: Conversation history ---
        history_frame = tk.Frame(self.paned_window, bg="#252526", width=220)
        history_frame.pack_propagate(False)
        self.paned_window.add(history_frame, weight=0)

        # New chat button
        btn_new_chat = tk.Button(history_frame, text="＋ Nouvelle conversation", bg="#0A84FF", fg="white",
                                font=("Segoe UI", 13, "bold"), bd=0, cursor="hand2", pady=8,
                                activebackground="#0063CC", activeforeground="white", command=self._new_conversation)
        btn_new_chat.pack(fill=tk.X, padx=10, pady=10)

        # List
        self.list_frame = tk.Frame(history_frame, bg="#252526")
        self.list_frame.pack(fill=tk.BOTH, expand=True, padx=5)

        self.conv_list = tk.Listbox(self.list_frame, bg="#252526", fg="#858585", bd=0,
                                   highlightthickness=0, selectbackground="#0058D0", selectforeground="#5E9DFF",
                                   font=("Segoe UI", 13), activestyle="none")
        self.conv_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_list = ttk.Scrollbar(self.list_frame, command=self.conv_list.yview)
        scroll_list.pack(side=tk.RIGHT, fill=tk.Y)
        self.conv_list.configure(yscrollcommand=scroll_list.set)

        self.conv_list.bind("<<ListboxSelect>>", self._on_conversation_selected)
        self.conv_list.bind("<Button-3>", self._show_history_menu)  # Right-click on Windows

        # --- Right: Chat area ---
        chat_frame = tk.Frame(self.paned_window, bg="#1E1E1E")
        self.paned_window.add(chat_frame, weight=1)

        # Top bar
        top_bar = tk.Frame(chat_frame, bg="#1E1E1E", pady=10)
        top_bar.pack(fill=tk.X)

        tk.Label(top_bar, text="🤖 Provider :", bg="#1E1E1E", fg="#E0E0E0", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=(15, 5))

        self.provider_var = tk.StringVar()
        providers = list(PROVIDERS.keys())
        if providers:
            self.provider_var.set(self.settings.get_default_provider() or providers[0])

        provider_menu = ttk.Combobox(top_bar, textvariable=self.provider_var, values=providers, state="readonly", width=15)
        provider_menu.pack(side=tk.LEFT)

        # --- Quick Actions Bar ---
        quick_bar = tk.Frame(chat_frame, bg="#252526", pady=6)
        quick_bar.pack(fill=tk.X, padx=10, pady=(0, 5))

        tk.Label(quick_bar, text="⚡ Actions rapides :", bg="#252526", fg="#858585",
                font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=(10, 8))

        for label, prompt in self.QUICK_ACTIONS:
            btn = tk.Button(quick_bar, text=label, bg="#333333", fg="#E0E0E0",
                          font=("Segoe UI", 11), bd=0, cursor="hand2", padx=10, pady=4,
                          activebackground="#0058D0", activeforeground="#5E9DFF",
                          command=lambda p=prompt, l=label: self._quick_action(p, l))
            btn.pack(side=tk.LEFT, padx=3)

        # Messages area
        msg_container = tk.Frame(chat_frame, bg="#1E1E1E")
        msg_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # We use a Text widget to display chat history because it supports rich formatting
        self.chat_display = tk.Text(msg_container, bg="#1E1E1E", fg="#FFFFFF", bd=0, highlightthickness=0,
                                   font=("Segoe UI", 14), wrap=tk.WORD, padx=20, pady=20, state=tk.DISABLED)
        self.chat_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_chat = ttk.Scrollbar(msg_container, command=self.chat_display.yview)
        scroll_chat.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_display.configure(yscrollcommand=scroll_chat.set)

        self._setup_chat_tags()

        # --- Attach bar (shows attached course) ---
        self.attach_bar = tk.Frame(chat_frame, bg="#333333")
        self.attach_label = tk.Label(self.attach_bar, text="", bg="#333333", fg="#5AC8FA",
                                    font=("Segoe UI", 11))
        self.attach_label.pack(side=tk.LEFT, padx=10, pady=4)
        btn_detach = tk.Button(self.attach_bar, text="✕", bg="#333333", fg="#FF453A", bd=0,
                              font=("Segoe UI", 11, "bold"), cursor="hand2",
                              activebackground="#333333", activeforeground="#FF6961",
                              command=self._detach_course)
        btn_detach.pack(side=tk.RIGHT, padx=10)
        # Don't pack attach_bar yet — only shown when a course is attached

        # Input area
        input_frame = tk.Frame(chat_frame, bg="#1E1E1E", pady=10, padx=10)
        input_frame.pack(fill=tk.X, side=tk.BOTTOM)

        # Attach course button
        btn_attach = tk.Button(input_frame, text="📎", bg="#333333", fg="#E0E0E0",
                              font=("Segoe UI", 16), bd=0, cursor="hand2", padx=8, pady=6,
                              activebackground="#0058D0", activeforeground="#5E9DFF",
                              command=self._attach_course)
        btn_attach.pack(side=tk.LEFT, padx=(0, 8), anchor=tk.S)

        self.input_text = tk.Text(input_frame, height=3, bg="#333333", fg="#FFFFFF", insertbackground="#FFFFFF",
                                 bd=1, highlightthickness=1, highlightbackground="#444444", highlightcolor="#0A84FF",
                                 font=("Segoe UI", 14), wrap=tk.WORD, padx=10, pady=10)
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.input_text.bind("<Return>", self._on_enter_pressed)
        self.input_text.bind("<Shift-Return>", lambda e: None)  # Allow multiline

        btn_send = tk.Button(input_frame, text="Envoyer", bg="#0A84FF", fg="white", font=("Segoe UI", 13, "bold"),
                            bd=0, cursor="hand2", padx=20, pady=10, activebackground="#0063CC", activeforeground="white",
                            command=self._send_message)
        btn_send.pack(side=tk.RIGHT, padx=(10, 0), anchor=tk.SE)

    def _setup_chat_tags(self):
        """Tags for formatting chat display."""
        base_font = "Segoe UI"
        code_font = "Consolas"

        self.chat_display.tag_configure("user_label", foreground="#0A84FF", font=(base_font, 12, "bold"), justify=tk.RIGHT, spacing1=10)
        self.chat_display.tag_configure("ai_label", foreground="#32D74B", font=(base_font, 12, "bold"), justify=tk.LEFT, spacing1=10)
        self.chat_display.tag_configure("user_msg", foreground="#FFFFFF", justify=tk.RIGHT, rmargin=20, lmargin1=100, lmargin2=100)

        # AI markdown tags
        self.chat_display.tag_configure("ai_normal", foreground="#FFFFFF", justify=tk.LEFT, lmargin1=20, rmargin=100, spacing3=5)
        self.chat_display.tag_configure("ai_bold", font=(base_font, 14, "bold"), foreground="#ffffff")
        self.chat_display.tag_configure("ai_italic", font=(base_font, 14, "italic"), foreground="#E0E0E0")
        self.chat_display.tag_configure("ai_code", font=(code_font, 13), foreground="#5AC8FA", background="#333333")
        self.chat_display.tag_configure("ai_h1", font=(base_font, 20, "bold"), foreground="#5E9DFF", spacing1=10)
        self.chat_display.tag_configure("ai_h2", font=(base_font, 18, "bold"), foreground="#5E9DFF", spacing1=8)
        self.chat_display.tag_configure("ai_h3", font=(base_font, 16, "bold"), foreground="#5E9DFF", spacing1=5)
        self.chat_display.tag_configure("ai_code_block", font=(code_font, 13), foreground="#FFFFFF", background="#333333", lmargin1=30, lmargin2=30, spacing1=5, spacing3=5)
        self.chat_display.tag_configure("ai_list", lmargin1=40, lmargin2=55)

    def _on_enter_pressed(self, event):
        if not event.state & 0x0001:  # No Shift
            self._send_message()
            return "break"
        return None

    # --- Course Context System ---

    def _scan_cours(self) -> str:
        """Scanne le dossier cours/ et retourne un résumé structuré du contenu."""
        course_texts = []
        total_chars = 0

        for root, dirs, files in os.walk(self.cours_dir):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            for filename in sorted(files):
                if not filename.endswith(".md"):
                    continue

                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, self.cours_dir)

                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                except Exception:
                    continue

                if not content:
                    continue

                # Limiter chaque fichier
                max_per_file = self.MAX_CONTEXT_CHARS // max(1, len(course_texts) + 1)
                if len(content) > max_per_file:
                    content = content[:max_per_file] + "\n[... tronqué ...]"

                entry = f"--- Fichier : {rel_path} ---\n{content}\n"
                total_chars += len(entry)

                if total_chars > self.MAX_CONTEXT_CHARS:
                    break

                course_texts.append(entry)

        if not course_texts:
            return ""

        return (
            "\n\n=== COURS DE L'ÉTUDIANT (pour contexte) ===\n"
            + "\n".join(course_texts)
            + "\n=== FIN DES COURS ===\n"
        )

    def _attach_course(self):
        """Ouvre un sélecteur pour joindre un cours spécifique au message."""
        # Lister les fichiers .md disponibles
        md_files = []
        for root, dirs, files in os.walk(self.cours_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in sorted(files):
                if f.endswith(".md"):
                    filepath = os.path.join(root, f)
                    rel_path = os.path.relpath(filepath, self.cours_dir)
                    md_files.append((rel_path, filepath))

        if not md_files:
            messagebox.showinfo("Aucun cours", "Aucun fichier .md trouvé dans le dossier cours/.\nCrée d'abord un cours dans l'onglet 'Mes cours'.")
            return

        # Fenêtre de sélection
        select_win = tk.Toplevel(self)
        select_win.title("📎 Joindre un cours")
        select_win.geometry("400x350")
        select_win.configure(bg="#1E1E1E")
        select_win.transient(self)
        select_win.grab_set()

        tk.Label(select_win, text="Sélectionne un cours à joindre :", bg="#1E1E1E", fg="#E0E0E0",
                font=("Segoe UI", 14, "bold")).pack(padx=15, pady=(15, 10), anchor="w")

        listbox = tk.Listbox(select_win, bg="#252526", fg="#FFFFFF", bd=0, highlightthickness=0,
                            selectbackground="#0058D0", selectforeground="#5E9DFF",
                            font=("Segoe UI", 13), activestyle="none")
        listbox.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        for rel_path, _ in md_files:
            listbox.insert(tk.END, f"📄 {rel_path}")

        def on_select():
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            rel_path, filepath = md_files[idx]
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                self._attached_course = {"name": rel_path, "content": content}
                self.attach_label.config(text=f"📎 {rel_path}")
                self.attach_bar.pack(fill=tk.X, padx=10, pady=(0, 5), before=self.input_text.master)
            except Exception as e:
                messagebox.showwarning("Erreur", f"Impossible de lire le fichier:\n{e}")
            select_win.destroy()

        tk.Button(select_win, text="Joindre", bg="#0A84FF", fg="white", font=("Segoe UI", 13, "bold"),
                 bd=0, cursor="hand2", padx=20, pady=8, activebackground="#0063CC",
                 command=on_select).pack(pady=(0, 15))

    def _detach_course(self):
        """Détache le cours joint."""
        self._attached_course = None
        self.attach_bar.pack_forget()

    def _quick_action(self, prompt: str, label: str):
        """Exécute une action rapide IA avec le contexte des cours."""
        if self._is_waiting:
            return

        # Vérifier si un cours est attaché
        course_context = ""
        if self._attached_course:
            course_context = f"\n\nVoici le cours sur lequel tu dois travailler :\n\n{self._attached_course['content']}"
        else:
            # Scanner automatiquement les cours
            scanned = self._scan_cours()
            if scanned:
                course_context = f"\n\nVoici les cours disponibles :\n\n{scanned}"
            else:
                messagebox.showinfo("Aucun cours",
                    "Aucun cours trouvé. Crée d'abord un cours dans 'Mes cours' "
                    "ou joindre un cours avec 📎.")
                return

        full_prompt = prompt + course_context
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", full_prompt)
        self._send_message()

    # --- Message Sending ---

    def _append_to_chat(self, text: str, role: str):
        self.chat_display.config(state=tk.NORMAL)

        time_str = datetime.now().strftime("%H:%M")

        if role == "user":
            self.chat_display.insert(tk.END, f"Toi ({time_str})\n", ("user_label",))
            # Truncate display for very long auto-generated prompts
            display_text = text
            if len(display_text) > 300:
                display_text = display_text[:200] + "\n[...contexte du cours joint...]\n"
            self.chat_display.insert(tk.END, f"{display_text}\n\n", ("user_msg",))
        else:
            self.chat_display.insert(tk.END, f"🤖 IA ({time_str})\n", ("ai_label",))

            # Format markdown for AI
            formatted_parts = markdown_to_plain_formatted(text)
            for part_text, tags in formatted_parts:
                ai_tags = tuple(f"ai_{tag}" for tag in tags) + ("ai_normal",)
                # Remap some tags to fit the chat display better
                remapped = []
                for t in ai_tags:
                    if t == "ai_normal": remapped.append(t)
                    elif t == "ai_bold": remapped.append(t)
                    elif t == "ai_italic": remapped.append(t)
                    elif t == "ai_code": remapped.append(t)
                    elif t == "ai_h1": remapped.append(t)
                    elif t == "ai_h2": remapped.append(t)
                    elif t == "ai_h3": remapped.append(t)
                    elif t == "ai_code_block": remapped.append(t)
                    elif t == "ai_list_bullet": remapped.append("ai_list")
                self.chat_display.insert(tk.END, part_text, tuple(remapped))
            self.chat_display.insert(tk.END, "\n\n")

        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def _send_message(self):
        if self._is_waiting:
            return

        content = self.input_text.get("1.0", tk.END).strip()
        if not content:
            return

        provider_name = self.provider_var.get()
        if not provider_name:
            messagebox.showwarning("Erreur", "Aucun provider sélectionné.")
            return

        api_key = self.settings.get_api_key(provider_name)
        if not api_key:
            messagebox.showwarning("Clé API manquante", f"La clé API pour {provider_name} n'est pas configurée.")
            return

        # Prepare UI and data
        self.input_text.delete("1.0", tk.END)
        self._is_waiting = True

        if not self.current_conversation_id:
            # Use first 30 chars of user message for title
            clean_title = content[:30].split("\n")[0]
            if len(content) > 30:
                clean_title += "..."
            self._new_conversation(switch_to=True, title=clean_title)

        self.current_messages.append({"role": "user", "content": content})
        self._append_to_chat(content, "user")

        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "L'IA réfléchit...\n\n", ("ai_label", "waiting"))
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

        # Save before sending
        self._save_conversation()

        # Build system prompt with course context
        system_prompt = self.SYSTEM_PROMPT

        # Inject scanned courses context into system prompt
        course_context = self._scan_cours()
        if course_context:
            system_prompt += (
                "\n\nL'étudiant a les cours suivants dans son application. "
                "Tu peux t'y référer pour contextualiser tes réponses :\n"
                + course_context
            )

        # If a course is specifically attached, add it prominently
        if self._attached_course:
            system_prompt += (
                f"\n\nL'étudiant a spécifiquement joint le cours '{self._attached_course['name']}'. "
                "Concentre-toi sur ce cours pour ta réponse.\n"
                f"Contenu du cours :\n{self._attached_course['content'][:self.MAX_CONTEXT_CHARS]}"
            )

        # Build messages for API
        api_messages = [{"role": "system", "content": system_prompt}] + self.current_messages
        model = self.settings.get_model(provider_name)

        # Clear attached course after sending
        self._detach_course()

        # Start thread
        threading.Thread(target=self._call_api, args=(provider_name, api_key, api_messages, model), daemon=True).start()

    def _call_api(self, provider_name, api_key, messages, model):
        try:
            provider = get_provider(provider_name, api_key)
            response = provider.send_message(messages, model)
            # Update UI on main thread
            self.after(0, self._on_api_success, response)
        except Exception as e:
            self.after(0, self._on_api_error, str(e))

    def _on_api_success(self, response: str):
        self._is_waiting = False

        # Remove waiting indicator
        self.chat_display.config(state=tk.NORMAL)
        idx = self.chat_display.search("L'IA réfléchit...", "1.0", tk.END)
        if idx:
            self.chat_display.delete(idx, f"{idx} lineend + 2 chars")
        self.chat_display.config(state=tk.DISABLED)

        self.current_messages.append({"role": "assistant", "content": response})
        self._append_to_chat(response, "assistant")
        self._save_conversation()

    def _on_api_error(self, error_msg: str):
        self._is_waiting = False

        self.chat_display.config(state=tk.NORMAL)
        idx = self.chat_display.search("L'IA réfléchit...", "1.0", tk.END)
        if idx:
            self.chat_display.delete(idx, f"{idx} lineend + 2 chars")
        self.chat_display.config(state=tk.DISABLED)

        messagebox.showerror("Erreur API", error_msg)
        if self.current_messages and self.current_messages[-1]["role"] == "user":
            self.current_messages.pop()  # Remove user message since it failed

    # --- Conversation Management ---

    def _new_conversation(self, switch_to=True, title=None):
        conv_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        conv_data = {
            "id": conv_id,
            "title": title or f"Conversation {timestamp}",
            "created": timestamp,
            "messages": [],
        }

        # Save empty
        conv_path = os.path.join(self.chat_history_dir, f"{conv_id}.json")
        with open(conv_path, "w", encoding="utf-8") as f:
            json.dump(conv_data, f, ensure_ascii=False, indent=2)

        # Add to list
        self.conv_list.insert(0, f"💬 {conv_data['title']}")
        # Store id mapping (dirty but works for simple list)
        if not hasattr(self, "_conv_ids"):
            self._conv_ids = []
        self._conv_ids.insert(0, conv_id)

        if switch_to:
            self.conv_list.selection_clear(0, tk.END)
            self.conv_list.selection_set(0)
            self.current_conversation_id = conv_id
            self.current_messages = []
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete("1.0", tk.END)
            self.chat_display.config(state=tk.DISABLED)

    def _load_conversation_list(self):
        self.conv_list.delete(0, tk.END)
        self._conv_ids = []
        conversations = []

        if os.path.exists(self.chat_history_dir):
            for filename in os.listdir(self.chat_history_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(self.chat_history_dir, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        conversations.append(data)
                    except:
                        pass

        # Sort newest first
        conversations.sort(key=lambda c: c.get("created", ""), reverse=True)

        for conv in conversations:
            self.conv_list.insert(tk.END, f"💬 {conv.get('title', 'Sans titre')}")
            self._conv_ids.append(conv["id"])

    def _on_conversation_selected(self, event):
        selection = self.conv_list.curselection()
        if not selection: return

        idx = selection[0]
        conv_id = self._conv_ids[idx]

        if conv_id == self.current_conversation_id: return

        self.current_conversation_id = conv_id
        self._load_conversation(conv_id)

    def _load_conversation(self, conv_id: str):
        conv_path = os.path.join(self.chat_history_dir, f"{conv_id}.json")
        if not os.path.exists(conv_path): return

        try:
            with open(conv_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            return

        self.current_messages = data.get("messages", [])

        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.config(state=tk.DISABLED)

        for msg in self.current_messages:
            self._append_to_chat(msg["content"], msg["role"])

    def _save_conversation(self):
        if not self.current_conversation_id: return

        conv_path = os.path.join(self.chat_history_dir, f"{self.current_conversation_id}.json")

        title = f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        for msg in self.current_messages:
            if msg["role"] == "user":
                raw = msg["content"][:30].split("\n")[0]
                title = raw
                if len(msg["content"]) > 30: title += "..."
                break

        conv_data = {
            "id": self.current_conversation_id,
            "title": title,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "messages": self.current_messages,
        }

        with open(conv_path, "w", encoding="utf-8") as f:
            json.dump(conv_data, f, ensure_ascii=False, indent=2)

        # Update list
        try:
            idx = self._conv_ids.index(self.current_conversation_id)
            self.conv_list.delete(idx)
            self.conv_list.insert(idx, f"💬 {title}")
            self.conv_list.selection_set(idx)
        except ValueError:
            pass

    def _show_history_menu(self, event):
        idx = self.conv_list.nearest(event.y)
        if idx >= 0:
            self.conv_list.selection_clear(0, tk.END)
            self.conv_list.selection_set(idx)

            menu = tk.Menu(self, tearoff=0, bg="#333333", fg="#E0E0E0")
            menu.add_command(label="✏️ Renommer", command=lambda: self._rename_conversation(idx))
            menu.add_command(label="🗑️ Supprimer", command=lambda: self._delete_conversation(idx))
            menu.post(event.x_root, event.y_root)

    def _rename_conversation(self, idx):
        conv_id = self._conv_ids[idx]
        old_title = self.conv_list.get(idx).replace("💬 ", "")

        new_title = simpledialog.askstring("Renommer", "Nouveau nom :", parent=self, initialvalue=old_title)
        if new_title and new_title.strip():
            # Update file
            conv_path = os.path.join(self.chat_history_dir, f"{conv_id}.json")
            if os.path.exists(conv_path):
                with open(conv_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["title"] = new_title.strip()
                with open(conv_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

            # Update list
            self.conv_list.delete(idx)
            self.conv_list.insert(idx, f"💬 {new_title.strip()}")
            self.conv_list.selection_set(idx)

    def _delete_conversation(self, idx):
        conv_id = self._conv_ids[idx]

        if messagebox.askyesno("Supprimer", "Supprimer cette conversation ?"):
            conv_path = os.path.join(self.chat_history_dir, f"{conv_id}.json")
            if os.path.exists(conv_path):
                os.remove(conv_path)

            self.conv_list.delete(idx)
            del self._conv_ids[idx]

            if conv_id == self.current_conversation_id:
                self.current_conversation_id = None
                self.current_messages = []
                self.chat_display.config(state=tk.NORMAL)
                self.chat_display.delete("1.0", tk.END)
                self.chat_display.config(state=tk.DISABLED)
