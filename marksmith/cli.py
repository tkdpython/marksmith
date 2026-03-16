"""Command-line interface for marksmith.

Invoked as::

    marksmith <action> [args...]
    python -m marksmith <action> [args...]

Actions are registered as argparse sub-commands.  As the tool grows, new
actions are added by creating a new sub-parser block and a corresponding
handler function (or module).
"""

import argparse
import sys

from marksmith import __version__
from marksmith.convert import md_to_docx


def main() -> None:
    """Entry point for the marksmith CLI."""
    parser = argparse.ArgumentParser(
        prog="marksmith",
        description="marksmith — a Markdown toolbox.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(
        dest="action",
        metavar="<action>",
        title="actions",
    )
    subparsers.required = True

    # ── convert ──────────────────────────────────────────────────────────────
    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert a Markdown file to another format (currently: .docx)",
        description=(
            "Convert a Markdown file to a DOCX document.\n\n"
            "FRONT-MATTER METADATA\n"
            "  The Markdown file may begin with a YAML front-matter block\n"
            "  (between '---' delimiters) containing document metadata:\n\n"
            "    ---\n"
            "    title: My Document\n"
            "    version: 1.0\n"
            "    author: Paul Cummings\n"
            "    date: 2026-03-16\n"
            "    classification: Internal\n"
            "    ---\n\n"
            "  Without a template, metadata is written to the DOCX core\n"
            "  properties (title, author, etc.).\n\n"
            "TEMPLATE SUPPORT  (coming soon — requires: pip install marksmith[template])\n"
            "  Provide a .docx template containing Jinja2-style placeholders\n"
            "  sourced from the front-matter metadata, e.g.:\n\n"
            "    {{ title }}   {{ version }}   {{ author }}   {{ date }}\n\n"
            "  Plus a special tag marking where the Markdown body is inserted:\n\n"
            "    {{ marksmith_content }}\n\n"
            "  Rendered via docxtpl (python-docx-template)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    convert_parser.add_argument(
        "input",
        help="Path to the input Markdown (.md) file",
    )
    convert_parser.add_argument(
        "output",
        help="Path to the output file (.docx)",
    )
    convert_parser.add_argument(
        "--template",
        metavar="TEMPLATE",
        default=None,
        help=(
            "Path to a .docx template file.  Placeholders in the template "
            "are filled from YAML front-matter metadata and the converted "
            "Markdown body is inserted at {{ marksmith_content }}. "
            "(Requires: pip install marksmith[template] — not yet implemented.)"
        ),
    )
    convert_parser.set_defaults(func=_cmd_convert)

    # ── future actions go here ────────────────────────────────────────────────
    # e.g.  lint, diff, toc, etc.

    args = parser.parse_args()
    args.func(args)


def _cmd_convert(args: argparse.Namespace) -> None:
    """Handle the 'convert' action."""
    try:
        md_to_docx(args.input, args.output, template_path=args.template)
        print(f"\u2713  Converted '{args.input}'  \u2192  '{args.output}'")  # noqa: T201
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)  # noqa: T201
        sys.exit(1)
    except NotImplementedError as exc:
        print(f"Not yet implemented: {exc}", file=sys.stderr)  # noqa: T201
        sys.exit(2)
    except Exception as exc:  # noqa: BLE001
        print(f"Conversion failed: {exc}", file=sys.stderr)  # noqa: T201
        sys.exit(1)
