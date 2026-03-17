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
from marksmith.convert import find_files_with_docx_path, md_to_docx, read_docx_path


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

    # ── to-docx ──────────────────────────────────────────────────────────────
    docx_parser = subparsers.add_parser(
        "to-docx",
        help="Convert Markdown file(s) to DOCX",
        description=(
            "Convert a Markdown file to a DOCX document.\n\n"
            "OUTPUT PATH\n"
            "  Provide an explicit output path as the second argument, or omit\n"
            "  it and set 'docx-path' in the file's YAML front-matter.\n"
            "  Environment variables in the path are expanded automatically:\n\n"
            "    ---\n"
            "    docx-path: '%MY_DOCS%\\\\Reports\\\\myfile.docx'\n"
            "    ---\n\n"
            "DIRECTORY MODE\n"
            "  Use --directory to recursively convert an entire directory tree.\n"
            "  Only files with 'docx-path' set in their front-matter are\n"
            "  converted; all others are silently skipped.\n\n"
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
            "TEMPLATE SUPPORT  (requires: pip install marksmith[template])\n"
            "  Provide a .docx template containing Jinja2-style placeholders\n"
            "  sourced from the front-matter metadata, e.g.:\n\n"
            "    {{ title }}   {{ version }}   {{ author }}   {{ date }}\n\n"
            "  Plus a special tag marking where the Markdown body is inserted:\n\n"
            "    {{ marksmith_content }}\n\n"
            "  Rendered via docxtpl (python-docx-template)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    docx_parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help=("Path to the input Markdown (.md) file. Omit when using --directory."),
    )
    docx_parser.add_argument(
        "output",
        nargs="?",
        default=None,
        help=("Path to the output .docx file. If omitted, the 'docx-path' key from the file's front-matter is used."),
    )
    docx_parser.add_argument(
        "--directory",
        metavar="DIR",
        default=None,
        help=(
            "Recursively convert all .md files under DIR that have a "
            "'docx-path' key in their front-matter. "
            "Cannot be used together with a positional input file."
        ),
    )
    docx_parser.add_argument(
        "--template",
        metavar="TEMPLATE",
        default=None,
        help=(
            "Path to a .docx template file.  Placeholders in the template "
            "are filled from YAML front-matter metadata and the converted "
            "Markdown body is inserted at {{ marksmith_content }}. "
            "If omitted, the MARKSMITH_TEMPLATE environment variable is used "
            "if set.  (Requires: pip install marksmith[template])"
        ),
    )
    docx_parser.set_defaults(func=_cmd_to_docx)

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


def _cmd_to_docx(args: argparse.Namespace) -> None:
    """Handle the 'to-docx' action."""
    # ── resolve template: explicit arg wins over MARKSMITH_TEMPLATE env var ───
    template = args.template or os.environ.get("MARKSMITH_TEMPLATE") or None

    # ── validate argument combinations ───────────────────────────────────────
    if args.directory and args.input:
        print("Error: --directory cannot be used together with a positional input file.", file=sys.stderr)  # noqa: T201
        sys.exit(1)
    if not args.directory and not args.input:
        print("Error: provide an input file or use --directory.", file=sys.stderr)  # noqa: T201
        sys.exit(1)

    # ── directory mode ───────────────────────────────────────────────────────
    if args.directory:
        try:
            files = find_files_with_docx_path(args.directory)
        except NotADirectoryError as exc:
            print(f"Error: {exc}", file=sys.stderr)  # noqa: T201
            sys.exit(1)

        if not files:
            print(f"No .md files with 'docx-path' found under '{args.directory}'.")  # noqa: T201
            return

        errors = 0
        for input_path, output_path in files:
            try:
                md_to_docx(input_path, output_path, template_path=template)
                print(f"  ✓  '{input_path}'  →  '{output_path}'")  # noqa: T201
            except Exception as exc:  # noqa: BLE001
                print(f"  ✗  '{input_path}': {exc}", file=sys.stderr)  # noqa: T201
                errors += 1

        total = len(files)
        print(f"\nDone: {total - errors}/{total} file(s) converted.")  # noqa: T201
        if errors:
            sys.exit(1)
        return

    # ── single file mode ───────────────────────────────────────────────────────
    output = args.output
    if not output:
        try:
            output = read_docx_path(args.input)
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)  # noqa: T201
            sys.exit(1)

    if not output:
        print(  # noqa: T201
            f"Error: no output path given and no 'docx-path' found in the front-matter of '{args.input}'.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        md_to_docx(args.input, output, template_path=template)
        print(f"✓  '{args.input}'  →  '{output}'")  # noqa: T201
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
