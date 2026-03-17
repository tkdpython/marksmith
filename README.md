# marksmith

> A Markdown toolbox — write docs in Markdown, ship them as polished DOCX or publish them to Confluence.

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

Optional extras for Confluence publishing:

```bash
pip install marksmith[confluence]
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
author:         Fred Bloggs
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

## Publishing to Confluence

Publish Markdown files directly to a Confluence space.

```bash
pip install marksmith[confluence]
```

### Credentials

Create a `.env` file with your Confluence URL and a Personal Access Token.
marksmith checks the following locations **in order**:

1. `.env` in the **current working directory**
2. `.env` in your **home directory** (`~/.env` on Linux/macOS, `%USERPROFILE%\.env` on Windows)

```dotenv
CONFLUENCE_URL=https://your-confluence.example.com
CONFLUENCE_TOKEN=your-personal-access-token
```

### Front-matter fields

Each file must include a YAML front-matter block that tells marksmith where to
publish the page:

```markdown
---
title: My Page Title
space: MYSPACE
parent_title: My Parent Page   # resolved by title; or use parent_id: 12345
labels:
  - my-label
page-properties:
  description: A short description of this page
  created_by: Fred Bloggs
  version: "1.0"
  document_status: DRAFT       # DRAFT (yellow) | PUBLISHED (green) | other (red)
---

# My Page Title

Content goes here...
```

| Field | Required | Description |
| --- | --- | --- |
| `title` | Yes | Confluence page title |
| `space` | Yes | Confluence space key |
| `parent_title` | One of | Title of the parent page (resolved at publish time) |
| `parent_id` | One of | Numeric Confluence page ID of the parent |
| `labels` | No | List of labels to apply |
| `page-properties` | No | Renders a Page Properties macro at the top of the page |

If the page already exists it is **updated**; otherwise it is **created**.

### Commands

```bash
# Publish a single file
marksmith to-confluence --upload-file path/to/my-doc.md

# Publish all .md files in a directory
marksmith to-confluence --upload-directory path/to/docs/

# Publish a tree of repositories (each must have a confluence.yml at its root)
marksmith to-confluence --process-repo-tree path/to/repos/
```

### Repository tree mode — `confluence.yml`

When using `--process-repo-tree`, each subdirectory that contains a
`confluence.yml` is processed.  The file defines the target space, parent page,
and index page title for that repository:

```yaml
repo-docs-path: docs/               # relative path to the docs directory
conflu-directory-title: My Service  # title of the index page created in Confluence
conflu-parent-id: "12345"           # Confluence page ID to create the index under
conflu-space-id: MYSPACE            # Confluence space key
```

All four fields are mandatory.

### Additional features

**Image attachments** — local images referenced in Markdown are automatically
uploaded as attachments to the published page.

**Confluence link replacements** — annotate a Markdown link with a
`<!-- replace_link(<page_id>) -->` comment to rewrite it as a Confluence
internal link at publish time:

```markdown
[See related page](./other.md) <!-- replace_link(98765) -->
```

---

## Roadmap

| Action | Description |
| --- | --- |
| `convert` | Markdown → DOCX ✔️ |
| `convert --template` | Merge into branded DOCX template ✔️ |
| `to-confluence` | Publish Markdown to Confluence ✔️ |
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
