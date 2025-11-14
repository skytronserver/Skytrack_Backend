#!/usr/bin/env python3
"""
Generate a simple certificate (HTML and optional PDF) containing `tuptime` output.

Usage:
    python3 scripts/generate_uptime_certificate.py [--html output.html] [--pdf output.pdf]

If `wkhtmltopdf` is available on PATH it will be used to create the PDF automatically.
Otherwise the script will still create an HTML certificate which you can convert to PDF using a browser or install `wkhtmltopdf`.
"""

import subprocess
import socket
import datetime
import shutil
import argparse
import sys
from pathlib import Path


def get_tuptime_output():
    try:
        out = subprocess.check_output(["sudo", "tuptime"], stderr=subprocess.STDOUT)
        return out.decode(errors="replace")
    except subprocess.CalledProcessError as e:
        return f"Error running tuptime:\n{return_bytes(e.output)}"
    except FileNotFoundError:
        return "tuptime is not installed or not found in PATH. Install it and try again."


def return_bytes(b):
    try:
        return b.decode(errors='replace')
    except Exception:
        return str(b)


def make_html(hostname, generated_at, tuptime_text, title="Uptime Certificate"):
    safe_text = """
    <pre style="font-family: monospace; font-size:14px; white-space: pre-wrap;">{}</pre>
    """.format(escape_html(tuptime_text))

    html = f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>{escape_html(title)}</title>
      <style>
        body {{ font-family: 'Helvetica Neue', Arial, sans-serif; padding: 36px; background: #f6f8fa; }}
        .card {{ max-width: 900px; margin: 24px auto; background: white; padding: 28px; box-shadow: 0 8px 30px rgba(0,0,0,0.08); border-radius: 8px; }}
        h1 {{ margin: 0 0 8px 0; font-size: 28px; }}
        .meta {{ color: #666; font-size: 14px; margin-bottom: 18px; }}
        .tuptime {{ background: #f3f6f9; padding: 12px; border-radius: 6px; overflow: auto; }}
        .footer {{ margin-top: 20px; color: #333; font-size: 13px; }}
      </style>
    </head>
    <body>
      <div class="card">
        <h1>{escape_html(title)}</h1>
        <div class="meta">Host: <strong>{escape_html(hostname)}</strong> &nbsp;•&nbsp; Generated: <strong>{escape_html(generated_at)}</strong></div>
        <div class="tuptime">{safe_text}</div>
        <div class="footer">This certificate contains the output of the <code>tuptime</code> tool. It reflects system uptime information as reported by the host.</div>
      </div>
    </body>
    </html>
    """
    return html


def escape_html(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;').replace("'", '&#39;'))


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    print(f"Wrote: {path}")


def convert_to_pdf(html_path: Path, pdf_path: Path):
    wk = shutil.which('wkhtmltopdf')
    if not wk:
        print("wkhtmltopdf not found on PATH; skipping automatic PDF conversion.")
        return False
    cmd = [wk, str(html_path), str(pdf_path)]
    print('Running:', ' '.join(cmd))
    try:
        subprocess.check_call(cmd)
        print(f"PDF generated: {pdf_path}")
        return True
    except subprocess.CalledProcessError as e:
        print('wkhtmltopdf failed with exit', e.returncode)
        return False


def main():
    parser = argparse.ArgumentParser(description='Generate uptime certificate (HTML and optional PDF).')
    parser.add_argument('--html', '-o', default='uptime_certificate.html', help='Output HTML file path')
    parser.add_argument('--pdf', '-p', default=None, help='Optional output PDF file path (if wkhtmltopdf is available)')
    args = parser.parse_args()

    tu_out = get_tuptime_output()
    hostname = socket.gethostname()
    generated_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')

    html = make_html(hostname, generated_at, tu_out)
    html_path = Path(args.html).resolve()
    write_file(html_path, html)

    pdf_path = None
    if args.pdf:
        pdf_path = Path(args.pdf).resolve()
    else:
        # if wkhtmltopdf exists, auto select same basename with .pdf
        if shutil.which('wkhtmltopdf'):
            pdf_path = html_path.with_suffix('.pdf')

    if pdf_path:
        convert_to_pdf(html_path, pdf_path)
    else:
        print('\nNo PDF path specified and wkhtmltopdf not available. To create a PDF, you can:')
        print(' - Open the generated HTML in a browser and Print -> Save as PDF')
        print(' - Or install wkhtmltopdf and re-run with --pdf output.pdf')

if __name__ == '__main__':
    main()
