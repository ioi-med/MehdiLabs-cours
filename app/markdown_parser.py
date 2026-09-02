"""
Markdown Parser — Parseur Markdown léger sans dépendance externe.
Convertit du texte Markdown en HTML basique.
"""

import re


def markdown_to_html(text: str) -> str:
    """Convertit du texte Markdown en HTML."""
    lines = text.split("\n")
    html_lines = []
    in_code_block = False
    code_lang = ""
    code_buffer = []
    in_list = False
    in_ordered_list = False
    in_table = False
    table_buffer = []

    def process_inline(line: str) -> str:
        """Traite le formatage inline (gras, italique, code, liens, images)."""
        # Images ![alt](url)
        line = re.sub(r'!\[([^\]]*)\]\(([^\)]+)\)',
                      r'<img src="\2" alt="\1" style="max-width:100%;border-radius:8px;">', line)
        # Links [text](url)
        line = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)',
                      r'<a href="\2" style="color:#5AC8FA;">\1</a>', line)
        # Bold **text** or __text__
        line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
        line = re.sub(r'__(.+?)__', r'<strong>\1</strong>', line)
        # Italic *text* or _text_
        line = re.sub(r'\*(.+?)\*', r'<em>\1</em>', line)
        line = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'<em>\1</em>', line)
        # Inline code `code`
        line = re.sub(r'`([^`]+)`',
                      r'<code style="background-color:#333333;padding:2px 6px;border-radius:4px;'
                      r'font-family:monospace;color:#5AC8FA;font-size:13px;">\1</code>', line)
        # Strikethrough ~~text~~
        line = re.sub(r'~~(.+?)~~', r'<del>\1</del>', line)
        return line

    for line in lines:
        stripped = line.strip()

        # Code blocks ```
        if stripped.startswith("```"):
            if in_code_block:
                code_text = "\n".join(code_buffer)
                code_text = code_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                html_lines.append(
                    f'<pre style="background-color:#1E1E1E;border:1px solid #3C3C3C;'
                    f'border-radius:8px;padding:16px;overflow-x:auto;margin:12px 0;">'
                    f'<code style="font-family:monospace;color:#FFFFFF;font-size:13px;">'
                    f'{code_text}</code></pre>'
                )
                code_buffer = []
                in_code_block = False
            else:
                in_code_block = True
                code_lang = stripped[3:].strip()
                code_buffer = []
            continue

        if in_code_block:
            code_buffer.append(line)
            continue

        # Close lists if needed
        if in_list and not re.match(r'^\s*[-*+]\s', stripped) and stripped:
            html_lines.append("</ul>")
            in_list = False
        if in_ordered_list and not re.match(r'^\s*\d+\.\s', stripped) and stripped:
            html_lines.append("</ol>")
            in_ordered_list = False

        # Table detection
        if "|" in stripped and not in_code_block:
            table_buffer.append(stripped)
            in_table = True
            continue
        elif in_table:
            _render_table(table_buffer, html_lines, process_inline)
            table_buffer = []
            in_table = False

        # Empty line
        if not stripped:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            if in_ordered_list:
                html_lines.append("</ol>")
                in_ordered_list = False
            html_lines.append("<br>")
            continue

        # Headers
        header_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if header_match:
            level = len(header_match.group(1))
            text_content = process_inline(header_match.group(2))
            sizes = {1: "28px", 2: "22px", 3: "18px", 4: "16px", 5: "14px", 6: "13px"}
            size = sizes.get(level, "13px")
            html_lines.append(
                f'<h{level} style="color:#5E9DFF;font-size:{size};'
                f'border-bottom:1px solid #3C3C3C;padding-bottom:8px;margin-top:24px;">'
                f'{text_content}</h{level}>'
            )
            continue

        # Horizontal rule
        if re.match(r'^[-*_]{3,}$', stripped):
            html_lines.append('<hr style="border:none;border-top:1px solid #3C3C3C;margin:24px 0;">')
            continue

        # Blockquote
        if stripped.startswith(">"):
            quote_text = process_inline(stripped.lstrip("> "))
            html_lines.append(
                f'<blockquote style="border-left:4px solid #0A84FF;padding-left:16px;'
                f'color:#858585;font-style:italic;margin:12px 0;">{quote_text}</blockquote>'
            )
            continue

        # Unordered list
        list_match = re.match(r'^(\s*)[-*+]\s+(.+)$', stripped)
        if list_match:
            if not in_list:
                html_lines.append('<ul style="padding-left:24px;">')
                in_list = True
            html_lines.append(f"<li>{process_inline(list_match.group(2))}</li>")
            continue

        # Ordered list
        ol_match = re.match(r'^(\s*)\d+\.\s+(.+)$', stripped)
        if ol_match:
            if not in_ordered_list:
                html_lines.append('<ol style="padding-left:24px;">')
                in_ordered_list = True
            html_lines.append(f"<li>{process_inline(ol_match.group(2))}</li>")
            continue

        # Regular paragraph
        html_lines.append(f"<p>{process_inline(stripped)}</p>")

    # Close any open elements
    if in_code_block and code_buffer:
        code_text = "\n".join(code_buffer)
        code_text = code_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html_lines.append(
            f'<pre style="background-color:#1E1E1E;border:1px solid #3C3C3C;'
            f'border-radius:8px;padding:16px;"><code>{code_text}</code></pre>'
        )
    if in_list:
        html_lines.append("</ul>")
    if in_ordered_list:
        html_lines.append("</ol>")
    if in_table and table_buffer:
        _render_table(table_buffer, html_lines, process_inline)

    return "\n".join(html_lines)


def _render_table(rows: list, html_lines: list, process_inline):
    """Rend un tableau Markdown en HTML."""
    if len(rows) < 2:
        # Not enough rows for a table, treat as paragraphs
        for row in rows:
            html_lines.append(f"<p>{process_inline(row)}</p>")
        return

    html_lines.append(
        '<table style="border-collapse:collapse;width:100%;margin:16px 0;">'
    )

    for i, row in enumerate(rows):
        cells = [c.strip() for c in row.strip("|").split("|")]

        # Skip separator row (---, :--:, etc.)
        if all(re.match(r'^:?-+:?$', c.strip()) for c in cells if c.strip()):
            continue

        tag = "th" if i == 0 else "td"
        style_bg = "background-color:#333333;color:#0A84FF;" if i == 0 else ""
        html_lines.append("<tr>")
        for cell in cells:
            html_lines.append(
                f'<{tag} style="border:1px solid #444444;padding:8px 12px;{style_bg}">'
                f'{process_inline(cell)}</{tag}>'
            )
        html_lines.append("</tr>")

    html_lines.append("</table>")


def markdown_to_plain_formatted(text: str) -> list:
    """Convertit du Markdown en liste de tuples (texte, tags) pour tkinter.Text.
    
    Retourne une liste de (text, tag_list) pour insertion dans un widget Text.
    Tags possibles : 'h1', 'h2', 'h3', 'bold', 'italic', 'code', 'code_block',
                      'link', 'list_bullet', 'blockquote', 'hr'
    """
    result = []
    lines = text.split("\n")
    in_code_block = False
    code_buffer = []

    for line in lines:
        stripped = line.strip()

        # Code blocks
        if stripped.startswith("```"):
            if in_code_block:
                result.append(("\n".join(code_buffer) + "\n", ("code_block",)))
                code_buffer = []
                in_code_block = False
            else:
                in_code_block = True
                code_buffer = []
            continue

        if in_code_block:
            code_buffer.append(line)
            continue

        # Headers
        header_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if header_match:
            level = len(header_match.group(1))
            tag = f"h{min(level, 3)}"
            result.append((header_match.group(2) + "\n", (tag,)))
            continue

        # HR
        if re.match(r'^[-*_]{3,}$', stripped):
            result.append(("─" * 40 + "\n", ("hr",)))
            continue

        # Blockquote
        if stripped.startswith(">"):
            text_content = stripped.lstrip("> ")
            result.append(("│ " + text_content + "\n", ("blockquote",)))
            continue

        # List items
        list_match = re.match(r'^\s*[-*+]\s+(.+)$', stripped)
        if list_match:
            result.append(("  • " + list_match.group(1) + "\n", ("list_bullet",)))
            continue

        ol_match = re.match(r'^\s*(\d+)\.\s+(.+)$', stripped)
        if ol_match:
            result.append((f"  {ol_match.group(1)}. " + ol_match.group(2) + "\n", ("list_bullet",)))
            continue

        # Regular text — process inline formatting
        if stripped:
            _process_inline_tags(stripped + "\n", result)
        else:
            result.append(("\n", ("normal",)))

    if in_code_block and code_buffer:
        result.append(("\n".join(code_buffer) + "\n", ("code_block",)))

    return result


def _process_inline_tags(text: str, result: list):
    """Traite le formatage inline pour le widget Text."""
    # Simplified: just detect bold, italic, code inline
    parts = re.split(r'(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)', text)
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            result.append((part[2:-2], ("bold",)))
        elif part.startswith("`") and part.endswith("`"):
            result.append((part[1:-1], ("code",)))
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            result.append((part[1:-1], ("italic",)))
        elif part:
            result.append((part, ("normal",)))
