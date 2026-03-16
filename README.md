# marksmith

> A Markdown toolbox — write docs in Markdown, ship them as polished DOCX.

[![PyPI](https://img.shields.io/pypi/v/marksmith)](https://pypi.org/project/marksmith/)
[![Python](https://img.shields.io/pypi/pyversions/marksmith)](https://pypi.org/project/marksmith/)
[![CI](https://github.com/tkdpython/marksmith/actions/workflows/ci.yml/badge.svg)](https://github.com/tkdpython/marksmith/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Installation

```bash
pip install marksmith
```

Optional extras for template support:

```bash
pip install marksmith[template]
```

---

## Quick start

```bash
# Using the installed script
marksmith convert my-doc.md output.docx

# Or via python -m
python -m marksmith convert my-doc.md output.docx
```

---

## Markdown front-matter

You can add a YAML front-matter block at the top of your Markdown file.
The metadata is written to the DOCX core properties (title, author, etc.)
and is also available as Jinja2 template variables when using `--template`.

```markdown
---
title:          My Document
version:        1.0
author:         Paul Cummings
date:           2026-03-16
classification: Internal
---

# My Document

Content goes here...
```

---

## Supported Markdown elements

| Element | Status |
| --- | --- |
| Headings H1 – H6 | ✅ |
| Bold / italic / inline code | ✅ |
| Fenced and indented code blocks | ✅ |
| Unordered lists (nested) | ✅ |
| Ordered lists (nested) | ✅ |
| Block-quotes | ✅ |
| Tables | ✅ |
| Thematic breaks (horizontal rules) | ✅ |
| Strikethrough | ✅ |
| Links (text rendered, no hyperlink) | ⚠️ |
| Images | ⚠️ placeholder text only |
| Inline HTML | ➖ ignored |

---

## Template support

Keep your content in plain Markdown while producing brand-consistent DOCX
output from a corporate template.

```bash
pip install marksmith[template]
marksmith convert my-doc.md output.docx --template company-template.docx
```

### How it works

1. Create a `.docx` template in Word with Jinja2-style placeholders for
   metadata sourced from your Markdown front-matter:

   ```jinja
   {{ title }}        {{ version }}      {{ author }}
   {{ date }}         {{ classification }}
   ```

2. Add a `{{p marksmith_content }}` paragraph **alone on its own line** at the
   exact point where the Markdown body should be inserted:

   ```text
   {{p marksmith_content }}
   ```

   > **Important:** Use `{{p ... }}` (with the `p` modifier), not `{{ ... }}`.
   > The `p` modifier inserts a paragraph-level sub-document rather than plain
   > text, so all headings, lists, tables, and code blocks are preserved.

3. Run the conversion — marksmith will:
   - Render all front-matter metadata into the Jinja2 placeholders.
   - Convert the Markdown body to native DOCX content.
   - Insert the body at `{{p marksmith_content }}`.
   - Save the merged document.

### Style inheritance

Content is inserted as a sub-document, so heading and paragraph styles are
matched by name against those in your template.  If your template defines
`Heading 1` with a custom font and colour, the converted content will pick
it up automatically.

---

## Roadmap

| Action | Description |
| --- | --- |
| `convert` | Markdown → DOCX ✔️ |
| `convert --template` | Merge into branded DOCX template ✔️ |
| `lint` | Validate Markdown style and structure |
| `toc` | Generate / update table of contents |
| `diff` | Show structural diff between two Markdown files |
| Images | Embed local images via `run.add_picture()` |
| Hyperlinks | Full OOXML hyperlink support |

---

## Development

```bash
git clone https://github.com/tkdpython/marksmith
cd marksmith
pip install -e .[dev,template]

# Run tests
pytest

# Lint
ruff check .
```

---

## Releasing

1. Bump `__version__` in `marksmith/__init__.py`.
2. Commit and push.
3. Create a GitHub Release with a tag matching the version (e.g. `v0.2.0`).
4. The [publish workflow](.github/workflows/publish.yml) fires automatically
   and publishes to PyPI via OIDC Trusted Publisher — no API tokens needed.

---

## License

MIT — see [LICENSE](LICENSE).
