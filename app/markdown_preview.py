"""
Markdown Preview — Widget de preview pour le Markdown (tkinter).
Utilise un widget Text avec des tags pour simuler un rendu HTML basique.
"""

import tkinter as tk
from tkinter import font
import webbrowser
from app.markdown_parser import markdown_to_plain_formatted


class MarkdownPreview(tk.Frame):
    """Preview basique du Markdown utilisant tkinter.Text."""

    def __init__(self, parent):
        super().__init__(parent, bg="#1E1E1E")
        
        self.text_widget = tk.Text(self, bg="#1E1E1E", fg="#FFFFFF", bd=0, 
                                  highlightthickness=0, wrap=tk.WORD, 
                                  font=("Segoe UI", 14), state=tk.DISABLED,
                                  padx=20, pady=20)
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(self, command=self.text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_widget.configure(yscrollcommand=scrollbar.set)
        
        self._setup_tags()
        
    def _setup_tags(self):
        """Configure les tags pour le formatage."""
        base_font = "Segoe UI"
        code_font = "Consolas" # Windows monospace font
        
        # Headers
        self.text_widget.tag_configure("h1", font=(base_font, 24, "bold"), foreground="#5E9DFF", spacing3=10, spacing1=15)
        self.text_widget.tag_configure("h2", font=(base_font, 20, "bold"), foreground="#5E9DFF", spacing3=8, spacing1=12)
        self.text_widget.tag_configure("h3", font=(base_font, 16, "bold"), foreground="#5E9DFF", spacing3=5, spacing1=10)
        
        # Text styles
        self.text_widget.tag_configure("bold", font=(base_font, 14, "bold"), foreground="#FFFFFF")
        self.text_widget.tag_configure("italic", font=(base_font, 14, "italic"), foreground="#E0E0E0")
        self.text_widget.tag_configure("code", font=(code_font, 13), foreground="#5AC8FA", background="#333333")
        
        # Blocks
        self.text_widget.tag_configure("code_block", font=(code_font, 13), foreground="#FFFFFF", background="#1E1E1E", lmargin1=10, lmargin2=10, rmargin=10, spacing1=5, spacing3=5)
        self.text_widget.tag_configure("blockquote", font=(base_font, 14, "italic"), foreground="#858585", lmargin1=15, lmargin2=15)
        self.text_widget.tag_configure("hr", foreground="#666666", justify=tk.CENTER)
        
        # Lists
        self.text_widget.tag_configure("list_bullet", lmargin1=20, lmargin2=35)
        
        # Default
        self.text_widget.tag_configure("normal", font=(base_font, 14), spacing1=2, spacing3=2)

    def update_content(self, md_text: str):
        """Met à jour la preview avec le texte Markdown."""
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete("1.0", tk.END)
        
        formatted_parts = markdown_to_plain_formatted(md_text)
        
        for text, tags in formatted_parts:
            self.text_widget.insert(tk.END, text, tags)
            
        self.text_widget.config(state=tk.DISABLED)

    def open_in_browser(self, html_content: str):
        """Ouvre le HTML complet dans le navigateur par défaut."""
        import tempfile
        import os
        
        # Create full HTML document
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
                    font-size: 16px;
                    line-height: 1.6;
                    color: #FFFFFF;
                    background-color: #1E1E1E;
                    padding: 40px;
                    max-width: 800px;
                    margin: 0 auto;
                }}
                h1, h2, h3 {{ color: #5E9DFF; }}
                a {{ color: #5AC8FA; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                code {{ background: #333333; padding: 2px 6px; border-radius: 4px; font-family: Consolas, monospace; color: #5AC8FA; }}
                pre {{ background: #1E1E1E; padding: 16px; border-radius: 8px; overflow-x: auto; }}
                pre code {{ background: none; padding: 0; color: #FFFFFF; }}
                blockquote {{ border-left: 4px solid #0A84FF; padding-left: 16px; color: #858585; font-style: italic; margin-left: 0; }}
                table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
                th, td {{ border: 1px solid #444444; padding: 8px 12px; }}
                th {{ background: #333333; }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        # Write to temp file and open
        fd, path = tempfile.mkstemp(suffix=".html")
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(full_html)
            
        webbrowser.open(f"file://{path}")
