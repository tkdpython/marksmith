"""Template-based DOCX rendering for marksmith.

Requires the ``marksmith[template]`` optional extra::

    pip install marksmith[template]

Template placeholders
---------------------
All YAML front-matter keys are available as Jinja2 variables, e.g.:

    {{ title }}    {{ version }}    {{ author }}    {{ date }}

The special ``marksmith_content`` variable holds the full converted Markdown
body as a sub-document.  Use the ``{{p ... }}`` paragraph-level tag to insert
it — **not** the inline ``{{ ... }}`` tag:

    {{p marksmith_content }}

This tag must appear **alone in its own paragraph** in the template.  Mixing
it with other text in the same paragraph will produce unexpected results.

Workflow
--------
1.  Create a ``.docx`` template in Word with Jinja2-style placeholders for
    metadata (title, version, author, etc.) and a ``{{p marksmith_content }}``
    paragraph at the desired content insertion point.

2.  Author your document in Markdown with a YAML front-matter header::

        ---
        title:          My Document
        version:        1.0
        author:         Paul Cummings
        date:           2026-03-16
        classification: Internal
        ---

        # Introduction

        Content goes here...

3.  Run the conversion::

        marksmith convert my-doc.md output.docx --template company-template.docx

Style inheritance
-----------------
Content paragraphs are inserted as a sub-document.  python-docx style names
(Heading 1, Heading 2, Normal, etc.) are preserved during insertion — if the
template defines styles with those names, the inserted content will
automatically pick them up.  This means heading fonts, colours, and spacing
all come from the template, not from the default Word styles.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from docxtpl import DocxTemplate

from marksmith.convert import (
    _apply_core_properties,
    _html_to_docx,
    _md_to_html,
    _parse_frontmatter,
)


def md_to_docx_templated(
    input_path: str,
    output_path: str,
    template_path: str,
) -> None:
    """Render a Markdown file into a ``.docx`` template.

    Parameters
    ----------
    input_path:
        Path to the source ``.md`` file (may include YAML front-matter).
    output_path:
        Destination path for the generated ``.docx`` file.  Parent
        directories are created automatically if they do not exist.
    template_path:
        Path to a ``.docx`` template file containing Jinja2-style
        placeholders.  Use ``{{p marksmith_content }}`` (alone in its own
        paragraph) to mark where the Markdown body is inserted.

    Raises
    ------
    FileNotFoundError
        If *template_path* does not exist.
    """
    if not Path(template_path).is_file():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    with open(input_path, encoding="utf-8") as fh:
        raw = fh.read()

    metadata, body = _parse_frontmatter(raw)
    html = _md_to_html(body)
    content_doc = _html_to_docx(html)
    _apply_core_properties(content_doc, metadata)

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp_path = tmp.name
        content_doc.save(tmp_path)

        tpl = DocxTemplate(template_path)
        sd = tpl.new_subdoc(tmp_path)

        # Build Jinja2 context: all front-matter values as strings + body subdoc.
        context: dict = {k: str(v) for k, v in metadata.items()}
        context["marksmith_content"] = sd

        tpl.render(context)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        tpl.save(output_path)
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
