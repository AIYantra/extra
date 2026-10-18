"""
Project Extra — HTML Clipboard Bridge
Injects rich formatted HTML into the OS clipboard so web editors
(Google Docs, Notion, Word Online) render genuine styles, headings, and tables
instead of unrendered raw plaintext markdown.
"""

from __future__ import annotations

import subprocess
import sys


def set_html_clipboard(html: str) -> bool:
    """
    Copies an HTML string into the Windows/macOS clipboard as rich text.
    """
    if sys.platform == "win32":
        # Escape single quotes in HTML for PowerShell here-string
        escaped_html = html.replace("'", "''")
        ps_script = f"""
        Add-Type -AssemblyName System.Windows.Forms
        $html = @'
{html}
'@
        [System.Windows.Forms.Clipboard]::SetText($html, [System.Windows.Forms.TextDataFormat]::Html)
        """
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-STA", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return res.returncode == 0
        except Exception:
            return False
    elif sys.platform == "darwin":
        # macOS pbcopy with text/html
        try:
            p = subprocess.Popen(["pbcopy", "-pboard", "general", "-Prefer", "rtf"], stdin=subprocess.PIPE)
            p.communicate(html.encode("utf-8"))
            return p.returncode == 0
        except Exception:
            return False
    return False


if __name__ == "__main__":
    test_html = "<h1>Test Executive Brief</h1><p>Paragraph with <b>bold text</b>.</p>"
    ok = set_html_clipboard(test_html)
    print("HTML Clipboard Set:", ok)
