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

Optional extras for template support *(coming soon)*:

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
and will be used to populate template placeholders once template support
is available.

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

## Roadmap

### Template support  *(next milestone)*

The goal is to allow teams to maintain brand-consistent DOCX output without
leaving Markdown.  The workflow will be:

1. A corporate `.docx` template carries the company's styles, logo, header,
   footer, and cover page.  Jinja2-style tags act as placeholders:

   ```jinja
   {{ title }}        {{ version }}      {{ author }}
   {{ date }}         {{ classification }}
   ```

2. A special `{{ marksmith_content }}` tag marks the exact point in the
   template where the converted Markdown body will be inserted.

3. Run the conversion:

   ```bash
   marksmith convert my-doc.md output.docx --template company-template.docx
   ```

   marksmith will:
   - Render all front-matter metadata into the Jinja2 placeholders.
   - Convert the Markdown body to DOCX-native content.
   - Insert the converted content at `{{ marksmith_content }}`.
   - Save the merged document as `output.docx`.

Implemented via [`docxtpl`](https://docxtpl.readthedocs.io/) — install the
`marksmith[template]` extra when this ships.

### Planned future actions

| Action | Description |
| --- | --- |
| `convert` | Markdown → DOCX *(available now)* |
| `convert --template` | Merge into branded DOCX template *(coming soon)* |
| `lint` | Validate Markdown style and structure |
| `toc` | Generate / update table of contents |
| `diff` | Show structural diff between two Markdown files |

---

## Development

```bash
git clone https://github.com/tkdpython/marksmith
cd marksmith
pip install -e .[dev]

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
