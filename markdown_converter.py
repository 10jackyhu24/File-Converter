from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import time
import uuid
from html.parser import HTMLParser
from pathlib import Path


class MarkdownRenderError(RuntimeError):
    """An error that can be safely surfaced by the conversion UI."""


class _SafeHtml(HTMLParser):
    """Keep Markdown's formatting while discarding active HTML and local resources."""

    TAGS = {
        "a", "blockquote", "br", "code", "del", "div", "em", "h1", "h2", "h3",
        "h4", "h5", "h6", "hr", "li", "ol", "p", "pre", "span", "strong",
        "sub", "sup", "table", "tbody", "td", "th", "thead", "tr", "ul",
    }
    DISCARD = {"script", "style", "iframe", "object", "embed", "svg", "math", "form"}
    VOID = {"br", "hr"}

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts: list[str] = []
        self.discard_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.discard_depth:
            if tag in self.DISCARD:
                self.discard_depth += 1
            return
        if tag in self.DISCARD:
            self.discard_depth = 1
            return
        if tag == "img":
            alt = next((value for key, value in attrs if key == "alt"), "image")
            self.parts.append(f'<span class="image-placeholder">[{html.escape(alt or "image")}]</span>')
            return
        if tag not in self.TAGS:
            return
        safe_attrs = []
        for key, value in attrs:
            if key == "class" and value and all(c.isalnum() or c in " _-" for c in value):
                safe_attrs.append(f'class="{html.escape(value, quote=True)}"')
            elif tag == "a" and key == "href" and value and value.lower().startswith(("https://", "http://", "mailto:", "#")):
                safe_attrs.append(f'href="{html.escape(value, quote=True)}"')
        suffix = " " + " ".join(safe_attrs) if safe_attrs else ""
        self.parts.append(f"<{tag}{suffix}>")

    def handle_endtag(self, tag: str) -> None:
        if self.discard_depth:
            if tag in self.DISCARD:
                self.discard_depth -= 1
            return
        if tag in self.TAGS and tag not in self.VOID:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self.discard_depth:
            self.parts.append(data)

    def handle_entityref(self, name: str) -> None:
        self.handle_data(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.handle_data(f"&#{name};")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def _sanitize_html(markdown_html: str) -> str:
    parser = _SafeHtml()
    parser.feed(markdown_html)
    parser.close()
    return "".join(parser.parts)


def _align_code_lines(markdown_html: str) -> str:
    """Keep each line number beside its source line even when code wraps."""

    pattern = re.compile(
        r'<div class="codehilite"><pre>(?:<span></span>)?<code>(.*?)</code></pre></div>',
        re.DOTALL,
    )
    number_pattern = re.compile(r'^<span class="linenos">\s*(\d+)</span>')

    def replace(match: re.Match[str]) -> str:
        rows = []
        for line in match.group(1).rstrip("\n").split("\n"):
            number = number_pattern.match(line)
            if number is None:
                return match.group(0)
            code = line[number.end():]
            rows.append(
                '<div class="code-line">'
                f'<span class="code-number">{number.group(1)}</span>'
                f'<span class="code-text">{code}</span>'
                '</div>'
            )
        return '<div class="codehilite">' + "".join(rows) + '</div>'

    return pattern.sub(replace, markdown_html)


def _extract_math(source: str) -> tuple[str, dict[str, str]]:
    """Stash math before Markdown interprets underscores or asterisks in TeX."""
    try:
        from latex2mathml.converter import convert
    except ImportError as exc:
        raise MarkdownRenderError("缺少 latex2mathml，請執行 pip install -r requirements.txt。") from exc

    markers: dict[str, str] = {}
    prefix = f"FCMATH{uuid.uuid4().hex.upper()}"

    def stash(latex: str, display: bool) -> str:
        marker = f"{prefix}{len(markers)}END"
        try:
            mathml = convert(latex.strip(), display="block" if display else "inline")
            markers[marker] = (
                f'<div class="math-display">{mathml}</div>' if display else
                f'<span class="math-inline">{mathml}</span>'
            )
        except Exception:
            delimiter = "$$" if display else "$"
            markers[marker] = f'<span class="math-fallback">{html.escape(delimiter + latex + delimiter)}</span>'
        return marker

    def inline_math(line: str) -> str:
        result: list[str] = []
        index = 0
        while index < len(line):
            if line[index] == "`":
                count = len(line[index:]) - len(line[index:].lstrip("`"))
                close = line.find("`" * count, index + count)
                if close >= 0:
                    result.append(line[index:close + count])
                    index = close + count
                    continue
            if line[index] == "\\" and line[index:index + 2] == "\\(":
                close = line.find("\\)", index + 2)
                if close >= 0:
                    result.append(stash(line[index + 2:close], False))
                    index = close + 2
                    continue
            if line[index] == "$" and line[index:index + 2] != "$$" and (index == 0 or line[index - 1] != "\\"):
                close = index + 1
                converted = False
                while close < len(line):
                    if line[close] == "$" and line[close - 1] != "\\" and line[close:close + 2] != "$$":
                        latex = line[index + 1:close]
                        if latex and not latex[0].isspace() and not latex[-1].isspace():
                            result.append(stash(latex, False))
                            index = close + 1
                            converted = True
                        break
                    close += 1
                if converted:
                    continue
            result.append(line[index])
            index += 1
        return "".join(result)

    output: list[str] = []
    lines = source.splitlines(keepends=True)
    fence_char = ""
    fence_length = 0
    fence_quote_depth = 0

    def quote_parts(line: str) -> tuple[str, str]:
        quote = re.match(r"^(?: {0,3}> ?)+", line)
        return (quote.group(), line[quote.end():]) if quote else ("", line)

    index = 0
    while index < len(lines):
        line = lines[index]
        quote_prefix, content = quote_parts(line)
        quote_depth = quote_prefix.count(">")
        if fence_char and quote_depth < fence_quote_depth:
            fence_char = ""
        fence_content = content if fence_quote_depth else line
        if fence_char:
            output.append(line)
            if re.match(rf"^ {{0,3}}{re.escape(fence_char)}{{{fence_length},}}\s*$", fence_content):
                fence_char = ""
            index += 1
            continue
        fence = re.match(r"^ {0,3}(`{3,}|~{3,})", content)
        if fence:
            fence_char = fence.group(1)[0]
            fence_length = len(fence.group(1))
            fence_quote_depth = quote_depth
            output.append(line)
            index += 1
            continue
        if content.startswith(("    ", "\t")):
            output.append(line)
            index += 1
            continue

        stripped = content.strip()
        delimiter = "$$" if stripped.startswith("$$") else "\\[" if stripped.startswith("\\[") else ""
        if delimiter:
            end_delimiter = "$$" if delimiter == "$$" else "\\]"
            pieces = [stripped[len(delimiter):]]
            consumed = 1
            while end_delimiter not in pieces[-1] and index + consumed < len(lines):
                next_prefix, next_content = quote_parts(lines[index + consumed])
                if next_prefix.count(">") != quote_depth:
                    break
                pieces.append(next_content.strip())
                consumed += 1
            joined = "\n".join(pieces)
            close = joined.find(end_delimiter)
            if close >= 0 and not joined[close + len(end_delimiter):].strip():
                # Keep blank separators inside the same quote, so the formula
                # becomes its own block without moving out of its container.
                output.append(
                    quote_prefix + "\n" + quote_prefix + stash(joined[:close], True)
                    + "\n" + quote_prefix + "\n"
                )
                index += consumed
                continue
        output.append(inline_math(line))
        index += 1
    return "".join(output), markers


def find_browser() -> Path | None:
    configured = os.environ.get("FILE_CONVERTER_BROWSER")
    candidates = [Path(configured)] if configured else []

    if os.name == "nt":
        for root_name in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
            root = os.environ.get(root_name)
            if root:
                candidates.extend(
                    [
                        Path(root) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                        Path(root) / "Google" / "Chrome" / "Application" / "chrome.exe",
                    ]
                )

    for command in ("msedge", "microsoft-edge", "google-chrome", "chromium", "chromium-browser"):
        resolved = shutil.which(command)
        if resolved:
            candidates.append(Path(resolved))

    return next((path for path in candidates if path.is_file()), None)


def _read_markdown(path: Path) -> str:
    if path.stat().st_size > 50 * 1024 * 1024:
        raise MarkdownRenderError("Markdown 檔案不可超過 50 MB。")
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="cp950")
        except UnicodeDecodeError as exc:
            raise MarkdownRenderError("Markdown 必須使用 UTF-8 編碼。") from exc


def _render_markdown_html(source_text: str, title: str, options: dict) -> str:
    try:
        import markdown
        from markdown.blockprocessors import ParagraphProcessor
        from pygments.formatters import HtmlFormatter
    except ImportError as exc:
        raise MarkdownRenderError(
            "缺少 Markdown 或 Pygments，請執行 pip install -r requirements.txt。"
        ) from exc

    class QuotedParagraphProcessor(ParagraphProcessor):
        """Allow a list to follow a quoted paragraph without a blank line."""

        LIST_START = re.compile(r"\n(?= {0,3}(?:[*+-]|\d+\.) +\S)")

        def run(self, parent, blocks):
            if parent.tag == "blockquote":
                block = blocks[0]
                # Inline code can span lines; list-like text inside it stays code.
                code_pattern = self.parser.md.inlinePatterns["backtick"].getCompiledRegExp()
                text = code_pattern.sub(lambda match: " " * len(match.group()), block)
                match = self.LIST_START.search(text)
                if match and not re.match(r"^ {0,3}(?:`{3,}|~{3,})", block):
                    blocks.pop(0)
                    self.parser.parseBlocks(parent, [block[:match.start()], block[match.end():]])
                    return
            super().run(parent, blocks)

    markdown_source, math_markers = _extract_math(source_text)
    renderer = markdown.Markdown(
        extensions=["tables", "fenced_code", "codehilite", "sane_lists"],
        extension_configs={
            "codehilite": {
                "linenos": "inline",
                "guess_lang": False,
                "css_class": "codehilite",
                "pygments_style": "friendly",
                "noclasses": False,
            }
        },
        output_format="html5",
    )
    renderer.parser.blockprocessors.register(QuotedParagraphProcessor(renderer.parser), "paragraph", 10)
    body = renderer.convert(markdown_source)
    body = _align_code_lines(_sanitize_html(body))
    for marker, mathml in math_markers.items():
        if mathml.startswith('<div class="math-display">'):
            body = re.sub(rf"<p>\s*{re.escape(marker)}\s*</p>", lambda _: mathml, body)
        body = body.replace(marker, mathml)

    orientation = options["orientation"]
    columns = options["columns"]
    margin_mm = options["margin_mm"]
    font_pt = options.get("font_pt", 10)
    pygments_css = HtmlFormatter(style="friendly").get_style_defs(".codehilite")

    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
@page {{ size: A4 {orientation}; margin: {margin_mm:g}mm; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
body {{
  color: #172b31;
  background: #fff;
  font-family: "Noto Sans CJK TC", "Microsoft JhengHei", "PingFang TC",
    "Noto Sans CJK JP", "Yu Gothic", "Meiryo", sans-serif;
  font-size: {font_pt:g}pt;
  line-height: 1.43;
  overflow-wrap: anywhere;
}}
.markdown-body {{
  column-count: {columns};
  column-gap: 5mm;
  column-fill: auto;
}}
h1, h2, h3, h4, h5, h6 {{
  margin: .8em 0 .28em;
  color: #123f49;
  line-height: 1.3;
  break-after: avoid;
}}
h1 {{ margin-top: 0; padding-bottom: .18em; border-bottom: 1px solid #9fc5c8; font-size: 1.7em; }}
h2 {{ padding-bottom: .16em; border-bottom: 1px solid #d6e2e3; font-size: 1.35em; }}
h3 {{ font-size: 1.16em; }}
p {{ margin: .28em 0 .55em; }}
ul, ol {{ margin: .3em 0 .6em; padding-left: 1.4em; }}
li {{ margin: .16em 0; }}
a {{ color: #0b7180; text-decoration: none; }}
blockquote {{
  margin: .55em 0;
  padding: .3em .55em;
  border-left: 3px solid #55aeb7;
  background: #f1f7f7;
  color: #455d63;
  break-inside: avoid;
}}
hr {{ border: 0; border-top: 1px solid #ccdada; margin: .8em 0; }}
code {{
  font-family: "Cascadia Mono", "Consolas", "Noto Sans Mono CJK TC", "MS Gothic", monospace;
  font-size: .83em;
}}
p code, li code, td code {{ padding: .1em .28em; border-radius: 3px; background: #edf3f3; color: #9b3e4b; }}
.codehilite {{
  margin: .5em 0;
  background: #f6f8f8;
  border: 1px solid #d6e0e1;
  border-radius: 4px;
  padding: .35em 0;
  font-family: "Cascadia Mono", "Consolas", "Noto Sans Mono CJK TC", "MS Gothic", monospace;
  font-size: .86em;
  line-height: 1.26;
}}
.code-line {{ display: flex; align-items: flex-start; min-width: 0; break-inside: avoid; }}
.code-number {{
  display: block;
  flex: 0 0 3.2em;
  padding-right: .42em;
  margin-right: .45em;
  border-right: 1px solid #d6e0e1;
  color: #8a9a9d;
  text-align: right;
  white-space: nowrap;
}}
.code-text {{ display: block; min-width: 0; flex: 1; padding-right: .45em; white-space: pre-wrap; overflow-wrap: anywhere; }}
.codehilite .code-text span {{ background: transparent !important; border: 0; }}
.math-inline math {{ font-family: "Cambria Math", "STIX Two Math", serif; }}
.math-display {{ margin: .45em 0 .65em; text-align: center; break-inside: avoid; }}
.math-display math {{ max-width: 100%; font-family: "Cambria Math", "STIX Two Math", serif; font-size: .94em; }}
.math-fallback {{ color: #9b3e4b; }}
table {{
  width: 100%;
  margin: .55em 0 .7em;
  border-collapse: collapse;
  font-size: 8.8pt;
  break-inside: avoid;
}}
table th, table td {{ padding: .38em .48em; border: 1px solid #bfcfd1; text-align: left; }}
table th {{ background: #e7f1f2; color: #173d45; font-weight: 700; }}
table tr:nth-child(even) td {{ background: #f7f9f9; }}
.image-placeholder {{ color: #75878b; font-style: italic; }}
{pygments_css}
</style>
</head>
<body><main class="markdown-body">{body}</main></body>
</html>"""


def _print_html_to_pdf(html_path: Path, pdf_path: Path, profile_dir: Path) -> None:
    browser = find_browser()
    if not browser:
        raise MarkdownRenderError(
            "找不到 Microsoft Edge、Google Chrome 或 Chromium，無法產生 PDF。"
        )

    command = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--disable-extensions",
        "--disable-sync",
        "--no-first-run",
        "--no-default-browser-check",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        f"--user-data-dir={profile_dir}",
        f"--print-to-pdf={pdf_path}",
        html_path.as_uri(),
    ]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except subprocess.TimeoutExpired as exc:
        raise MarkdownRenderError("Markdown 轉 PDF 時間過長，已停止處理。") from exc

    # Some Chromium builds finish the file a fraction after their main process exits.
    for _ in range(20):
        if pdf_path.is_file() and pdf_path.stat().st_size > 0:
            break
        time.sleep(0.1)

    # Edge can return a non-zero status on Windows when a short-lived cache
    # process is still closing, even though the PDF was written successfully.
    # The produced file is the reliable success signal for print-to-PDF.
    if not pdf_path.is_file() or pdf_path.stat().st_size == 0:
        details = result.stderr.strip().splitlines()
        message = details[-1] if details else "瀏覽器沒有產生輸出檔案"
        raise MarkdownRenderError(f"Markdown 轉 PDF 失敗：{message}")


def _add_page_numbers(source: Path, destination: Path, position: str, margin_mm: float) -> None:
    if position == "none":
        shutil.copyfile(source, destination)
        return

    try:
        import fitz
    except ImportError as exc:
        raise MarkdownRenderError("缺少 PyMuPDF，無法加入頁碼。") from exc

    vertical, horizontal = position.split("_")
    alignments = {
        "left": fitz.TEXT_ALIGN_LEFT,
        "center": fitz.TEXT_ALIGN_CENTER,
        "right": fitz.TEXT_ALIGN_RIGHT,
    }
    document = fitz.open(source)
    try:
        for number, page in enumerate(document, start=1):
            page_rect = page.rect
            margin_points = max(14.0, margin_mm * 72 / 25.4)
            side_inset = min(margin_points * 0.65, 36)
            if vertical == "top":
                box = fitz.Rect(
                    side_inset, 3, page_rect.width - side_inset, max(15, margin_points - 3)
                )
            else:
                box = fitz.Rect(
                    side_inset,
                    page_rect.height - max(15, margin_points - 3),
                    page_rect.width - side_inset,
                    page_rect.height - 3,
                )
            page.insert_textbox(
                box,
                str(number),
                fontname="helv",
                fontsize=8.5,
                color=(0.34, 0.42, 0.44),
                align=alignments[horizontal],
                overlay=True,
            )
        document.save(destination, garbage=3, deflate=True)
    finally:
        document.close()


def render_markdown_pdf(source: Path, destination: Path, options: dict, work_dir: Path) -> None:
    source_text = _read_markdown(source)
    html_text = _render_markdown_html(source_text, source.stem, options)
    html_path = work_dir / "document.html"
    raw_pdf = work_dir / "rendered.pdf"
    profile_dir = work_dir / "browser-profile"
    html_path.write_text(html_text, encoding="utf-8")
    _print_html_to_pdf(html_path, raw_pdf, profile_dir)
    _add_page_numbers(raw_pdf, destination, options["page_number"], options["margin_mm"])
