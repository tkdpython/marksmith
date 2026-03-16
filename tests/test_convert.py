"""Tests for marksmith.convert."""

import pytest

from marksmith.convert import _md_to_html, _parse_frontmatter, md_to_docx

# ── _parse_frontmatter ────────────────────────────────────────────────────────


def test_parse_frontmatter_extracts_metadata():
    raw = "---\ntitle: My Doc\nversion: 1.0\n---\n# Hello"
    meta, body = _parse_frontmatter(raw)
    assert meta["title"] == "My Doc"
    assert meta["version"] == 1.0


def test_parse_frontmatter_returns_body():
    raw = "---\ntitle: Test\n---\n# Hello\n\nSome text."
    _, body = _parse_frontmatter(raw)
    assert "# Hello" in body
    assert "Some text." in body


def test_parse_frontmatter_no_frontmatter():
    raw = "# Hello\n\nJust content, no metadata."
    meta, body = _parse_frontmatter(raw)
    assert meta == {}
    assert "# Hello" in body


def test_parse_frontmatter_empty_frontmatter():
    raw = "---\n---\n# Hello"
    meta, body = _parse_frontmatter(raw)
    assert meta == {}
    assert "# Hello" in body


# ── _md_to_html ───────────────────────────────────────────────────────────────


def test_md_to_html_heading():
    html = _md_to_html("# Hello World")
    assert "<h1>Hello World</h1>" in html


def test_md_to_html_bold():
    html = _md_to_html("This is **bold** text.")
    assert "<strong>bold</strong>" in html


def test_md_to_html_code_block():
    html = _md_to_html("```python\nprint('hi')\n```")
    assert "<pre>" in html
    assert "<code" in html  # may include class="language-python"


def test_md_to_html_table():
    md = "| A | B |\n|---|---|\n| 1 | 2 |"
    html = _md_to_html(md)
    assert "<table>" in html


def test_md_to_html_unordered_list():
    html = _md_to_html("- item one\n- item two")
    assert "<ul>" in html
    assert "<li>" in html


def test_md_to_html_ordered_list():
    html = _md_to_html("1. first\n2. second")
    assert "<ol>" in html


# ── md_to_docx ────────────────────────────────────────────────────────────────


def test_md_to_docx_file_not_found():
    with pytest.raises(FileNotFoundError, match="nonexistent.md"):
        md_to_docx("nonexistent.md", "output.docx")


def test_md_to_docx_unsupported_format(tmp_path):
    md_file = tmp_path / "test.md"
    md_file.write_text("# Hello")
    with pytest.raises(ValueError, match=".txt"):
        md_to_docx(str(md_file), str(tmp_path / "output.txt"))


def test_md_to_docx_template_raises_not_implemented(tmp_path):
    md_file = tmp_path / "test.md"
    md_file.write_text("# Hello")
    with pytest.raises(NotImplementedError):
        md_to_docx(str(md_file), str(tmp_path / "output.docx"), template_path="tmpl.docx")


def test_md_to_docx_creates_file(tmp_path):
    md_file = tmp_path / "test.md"
    md_file.write_text("# Hello\n\nThis is a paragraph.")
    output_file = tmp_path / "output.docx"
    md_to_docx(str(md_file), str(output_file))
    assert output_file.exists()
    assert output_file.stat().st_size > 0


def test_md_to_docx_with_frontmatter(tmp_path):
    md_file = tmp_path / "test.md"
    md_file.write_text("---\ntitle: My Doc\nauthor: Test Author\n---\n# Hello")
    output_file = tmp_path / "output.docx"
    md_to_docx(str(md_file), str(output_file))
    assert output_file.exists()


def test_md_to_docx_creates_parent_dirs(tmp_path):
    md_file = tmp_path / "test.md"
    md_file.write_text("# Hello")
    output_file = tmp_path / "subdir" / "nested" / "output.docx"
    md_to_docx(str(md_file), str(output_file))
    assert output_file.exists()


def test_md_to_docx_all_block_elements(tmp_path):
    """Smoke test covering all supported block-level elements."""
    md = """---
title: Smoke Test
---

# Heading 1

## Heading 2

### Heading 3

A paragraph with **bold**, *italic*, `inline code`, and ~~strikethrough~~.

- Bullet one
- Bullet two
  - Nested bullet

1. First
2. Second

> A blockquote paragraph.

```python
def hello():
    print("hello")
```

| Col A | Col B |
| --- | --- |
| val 1 | val 2 |

---
"""
    md_file = tmp_path / "smoke.md"
    md_file.write_text(md)
    output_file = tmp_path / "smoke.docx"
    md_to_docx(str(md_file), str(output_file))
    assert output_file.exists()
    assert output_file.stat().st_size > 0
