"""Command-line interface for marksmith.

Invoked as::

    marksmith <action> [args...]
    python -m marksmith <action> [args...]

Actions are registered as argparse sub-commands.  As the tool grows, new
actions are added by creating a new sub-parser block and a corresponding
handler function (or module).
"""

import argparse
import os
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
            "    author: Fred Bloggs\n"
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

    # ── to-confluence ──────────────────────────────────────────────────────────
    confluence_parser = subparsers.add_parser(
        "to-confluence",
        help="Publish Markdown files to Confluence",
        description=(
            "Publish Markdown files to Confluence using YAML front-matter metadata.\n\n"
            "CREDENTIALS\n"
            "  Set CONFLUENCE_URL and CONFLUENCE_TOKEN in a .env file.\n"
            "  Checked in order:\n"
            "    1. .env in the current working directory\n"
            "    2. .env in your home directory (~/.env)\n\n"
            "FRONT-MATTER\n"
            "  Each Markdown file must begin with a YAML front-matter block:\n\n"
            "    ---\n"
            "    title: My Page\n"
            "    space: MYSPACE\n"
            "    parent_title: Parent Page   # or parent_id: 12345\n"
            "    labels:\n"
            "      - my-label\n"
            "    ---\n\n"
            "REQUIRES\n"
            "  pip install marksmith[confluence]"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    confluence_group = confluence_parser.add_mutually_exclusive_group(required=True)
    confluence_group.add_argument(
        "--upload-file",
        metavar="FILE",
        dest="markdown_file",
        help="Path to a single Markdown file to publish",
    )
    confluence_group.add_argument(
        "--upload-directory",
        metavar="DIR",
        dest="markdown_directory",
        help="Path to a directory — all .md files are published",
    )
    confluence_group.add_argument(
        "--process-repo-tree",
        metavar="DIR",
        dest="repo_tree_path",
        help="Directory of repositories — each must contain a confluence.yml at its root",
    )
    confluence_parser.set_defaults(func=_cmd_to_confluence)

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


def _cmd_to_confluence(args: argparse.Namespace) -> None:
    """Handle the 'to-confluence' action."""
    try:
        from marksmith.confluence import ConfluenceUpdater, _load_env  # noqa: PLC0415
    except ImportError:
        print(  # noqa: T201
            "Error: the 'confluence' extra is required.\n  pip install marksmith[confluence]",
            file=sys.stderr,
        )
        sys.exit(1)

    _load_env()

    confluence_url = os.environ.get("CONFLUENCE_URL")
    confluence_token = os.environ.get("CONFLUENCE_TOKEN")

    if not confluence_url or not confluence_token:
        print(  # noqa: T201
            "Error: CONFLUENCE_URL and CONFLUENCE_TOKEN must be set.\n"
            "  Add them to .env in the current directory or ~/.env",
            file=sys.stderr,
        )
        sys.exit(1)

    cu = ConfluenceUpdater(confluence_url=confluence_url, confluence_token=confluence_token)

    try:
        if args.markdown_file:
            cu.publish_file(args.markdown_file)
        elif args.markdown_directory:
            cu.publish_directory(args.markdown_directory)
        elif args.repo_tree_path:
            cu.process_repo_tree(args.repo_tree_path)
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)  # noqa: T201
        sys.exit(1)
