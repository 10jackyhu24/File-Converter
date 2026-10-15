from __future__ import annotations

import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import fitz

from markdown_converter import _extract_math, _render_markdown_html, render_markdown_pdf


QUOTED_LIST = (
    "> **說明：** 示範 C++ 內建 `std::priority_queue`（位於 `<queue>`）的最大堆、最小堆與自訂結構排序。\n"
    "> - **預設：** 最大堆，最大的元素位於頂端。\n"
    "> - **最小堆：** 使用 `std::greater`，最小的元素位於頂端；圖論常搭配 `std::pair`。\n"
    "> - **自訂排序：** 在自訂 `struct` 中重載 `<` 運算子。\n"
)
FORMULA = r"x \div a \equiv x \times a^{p-2} \pmod{p}"
OPTIONS = {"orientation": "portrait", "columns": 1, "margin_mm": 20}


class MarkdownQuoteTests(unittest.TestCase):
    def render_body(self, source: str) -> ET.Element:
        rendered = _render_markdown_html(source, "quoted-markdown", OPTIONS)
        body = rendered.split("<body>", 1)[1].split("</body>", 1)[0]
        return ET.fromstring(body)

    def test_list_immediately_after_quoted_paragraph(self):
        body = self.render_body(QUOTED_LIST)
        quote = body.find("blockquote")
        self.assertIsNotNone(quote)
        self.assertEqual([child.tag for child in quote], ["p", "ul"])
        self.assertEqual(len(quote.findall("ul/li")), 3)
        self.assertEqual(quote.find("ul/li/strong").text, "預設：")
        self.assertIn("<queue>", "".join(quote.itertext()))

    def test_list_markers_and_nested_quotes(self):
        for marker, tag in [("-", "ul"), ("*", "ul"), ("+", "ul"), ("1.", "ol")]:
            with self.subTest(marker=marker):
                body = self.render_body(f"> > Description\n> > {marker} First\n> > {marker} Second\n")
                quote = body.find("blockquote/blockquote")
                self.assertEqual(len(quote.findall(f"{tag}/li")), 2)

    def test_display_math_inside_quotes(self):
        for prefix in ("", "> ", "> > "):
            for opening, closing in (("$$", "$$"), (r"\[", r"\]")):
                for multiline in (False, True):
                    with self.subTest(prefix=prefix, opening=opening, multiline=multiline):
                        source = (
                            f"{prefix}{opening}\n{prefix}{FORMULA}\n{prefix}{closing}\n"
                            if multiline else f"{prefix}{opening} {FORMULA} {closing}\n"
                        )
                        body = self.render_body(source)
                        container = body
                        for _ in range(prefix.count(">")):
                            container = container.find("blockquote")
                            self.assertIsNotNone(container)
                        display = container.find("div[@class='math-display']")
                        self.assertIsNotNone(display)
                        ns = {"m": "http://www.w3.org/1998/Math/MathML"}
                        self.assertIsNotNone(display.find("m:math", ns))
                        self.assertIsNotNone(display.find(".//m:msup", ns))
                        text = "".join(display.itertext())
                        for operator in ("÷", "≡", "×", "mod"):
                            self.assertIn(operator, text)
                        self.assertNotIn("\\", text)

    def test_display_math_keeps_surrounding_quote_content(self):
        body = self.render_body(f"> Before\n> $$ {FORMULA} $$\n> After\n\nOutside\n")
        quote = body.find("blockquote")
        self.assertEqual([child.tag for child in quote], ["p", "div", "p"])
        self.assertEqual(quote.find("p").text, "Before")
        self.assertEqual(quote.findall("p")[-1].text, "After")
        self.assertEqual(body.find("p").text, "Outside")

    def test_code_is_preserved(self):
        sources = [
            "```markdown\n" + QUOTED_LIST + f"> $$ {FORMULA} $$\n```\n",
            f"> ```latex\n> $$ {FORMULA} $$\n> ```\n",
            f">     $$ {FORMULA} $$\n",
            f"> `$$ {FORMULA} $$`\n",
        ]
        for source in sources:
            with self.subTest(source=source):
                extracted, markers = _extract_math(source)
                self.assertEqual(markers, {})
                self.assertEqual(extracted, source)

    def test_list_markers_inside_quoted_code_stay_literal(self):
        for source in (
            "> `Example\n> - literal item\n> end`\n",
            "> ```markdown\n> Example\n> - literal item\n> ```\n",
            "> ~~~markdown\n> Example\n> - literal item\n> ~~~\n",
            ">     Example\n>     - literal item\n",
        ):
            with self.subTest(source=source):
                body = self.render_body(source)
                self.assertIsNone(body.find(".//ul"))
                self.assertIn("- literal item", "".join(body.itertext()))

    def test_unclosed_math_does_not_consume_other_quotes(self):
        body = self.render_body(
            "> $$\n> unfinished\n\nOutside\n\n> $$\n> Another quote\n"
        )
        self.assertIsNone(body.find(".//div[@class='math-display']"))
        self.assertEqual(body.find("p").text, "Outside")

    def test_quoted_list_and_formula_in_pdf(self):
        with tempfile.TemporaryDirectory() as directory:
            work_dir = Path(directory)
            source = work_dir / "quoted-markdown.md"
            destination = work_dir / "quoted-markdown.pdf"
            source.write_text(QUOTED_LIST + f"\n> $$ {FORMULA} $$\n", encoding="utf-8")
            render_markdown_pdf(source, destination, {**OPTIONS, "page_number": "none"}, work_dir)
            with fitz.open(destination) as document:
                self.assertEqual(document.page_count, 1)
                page = document[0]
                positions = [page.search_for(label) for label in ("預設：", "最小堆：", "自訂排序：")]
                self.assertTrue(all(positions), positions)
                self.assertLess(positions[0][0].y0, positions[1][0].y0)
                self.assertLess(positions[1][0].y0, positions[2][0].y0)
                text = page.get_text()
                for operator in ("÷", "≡", "×", "mod"):
                    self.assertIn(operator, text)
                self.assertNotIn("$$", text)
                self.assertNotIn(r"\pmod", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
