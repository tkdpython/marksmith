"""
Confluence publisher for marksmith.

Publishes Markdown files to Confluence pages using YAML front-matter metadata
to control the target space, parent page, title, labels, and document status.

Requires the ``marksmith[confluence]`` optional extra::

    pip install marksmith[confluence]

Configuration
-------------
Credentials are loaded from a ``.env`` file.  The following locations are
checked in order:

1. ``.env`` in the current working directory.
2. ``.env`` in the user's home directory (``~/.env``).

Required variables::

    CONFLUENCE_URL=https://your-confluence.example.com
    CONFLUENCE_TOKEN=your-personal-access-token

Markdown front-matter
---------------------
Each Markdown file must contain a YAML front-matter block at the top::

    ---
    title: My Page Title
    space: MYSPACE
    parent_title: My Parent Page   # resolved by title if parent_id not given
    parent_id: 12345               # optional — takes precedence over parent_title
    labels:
      - my-label
    page-properties:
      description: A short description
      created_by: Fred Bloggs
      version: "1.0"
      document_status: DRAFT       # DRAFT (yellow) | PUBLISHED (green) | other (red)
    ---

``confluence.yml`` (repo-tree mode)
------------------------------------
Place a ``confluence.yml`` at the root of each repository to be published::

    repo-docs-path: docs/
    conflu-directory-title: My Service
    conflu-parent-id: "12345"
    conflu-space-id: MYSPACE

All four fields are mandatory.
"""

from __future__ import annotations

import mimetypes
import os
import re
from pathlib import Path
from typing import Any

import mistune
import yaml
from atlassian import Confluence
from md2cf.api import MinimalConfluence
from md2cf.confluence_renderer import ConfluenceRenderer


def _load_env() -> None:
    """
    Load ``.env`` from the current working directory, falling back to ``~/.env``.

    Works on both Windows and Linux.  Does nothing silently if neither file
    exists.
    """
    from dotenv import load_dotenv  # noqa: PLC0415

    cwd_env = Path.cwd() / ".env"
    home_env = Path.home() / ".env"

    if cwd_env.is_file():
        load_dotenv(cwd_env)
    elif home_env.is_file():
        load_dotenv(home_env)


class ConfluenceRepoConfig:
    """
    Loads and validates a ``confluence.yml`` file at the root of a repository.

    Parameters
    ----------
    repo_path:
        Absolute or relative path to the repository directory.  The directory
        must contain a ``confluence.yml`` file.

    """

    def __init__(self, repo_path: str = "") -> None:
        self.valid = True
        self.space: str = ""
        self.parent_id: str = ""
        self.directory_title: str = ""
        self.docs_path: str = ""

        if not os.path.exists(repo_path):
            print(f"Repo path does not exist: {repo_path}")  # noqa: T201  # noqa: T201
            self.valid = False
            return

        self.repo_path = repo_path
        self._load_config()

    def _load_config(self) -> None:
        confluence_yaml_path = os.path.join(self.repo_path, "confluence.yml")
        try:
            with open(confluence_yaml_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)

            mandatory_fields = [
                "repo-docs-path",
                "conflu-directory-title",
                "conflu-parent-id",
                "conflu-space-id",
            ]
            for field in mandatory_fields:
                if field not in config:
                    print(f"Missing required field '{field}' in {confluence_yaml_path}")  # noqa: T201
                    self.valid = False

            if self.valid:
                self.space = config["conflu-space-id"]
                self.parent_id = config["conflu-parent-id"]
                self.directory_title = config["conflu-directory-title"]
                self.docs_path = os.path.join(self.repo_path, config["repo-docs-path"])

        except FileNotFoundError:
            print(f"No confluence.yml found at {confluence_yaml_path}")  # noqa: T201
            self.valid = False
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to load confluence.yml: {exc}")  # noqa: T201
            self.valid = False


class ConfluenceMarkdownFile:
    """
    Parses a Markdown file and prepares its content for publishing to Confluence.

    The file must contain a YAML front-matter block.  At minimum, ``title``,
    ``space``, and one of ``parent_id`` / ``parent_title`` must be present.

    Parameters
    ----------
    file_path:
        Path to the ``.md`` file.
    space:
        Confluence space key override (overridden by front-matter if present).
    parent_id:
        Parent page ID override.
    parent_title:
        Parent page title override (used to look up the ID at publish time).

    """

    def __init__(
        self,
        file_path: str,
        space: str | None = None,
        parent_id: str | None = None,
        parent_title: str | None = None,
    ) -> None:
        if not file_path:
            raise ValueError("ConfluenceMarkdownFile requires a file_path")

        self.file_path = file_path
        self.title: str | None = None
        self.page_properties: dict = {}
        self.space = space
        self.parent_title = parent_title
        self.parent_id = parent_id
        self.attachments: list[str] = []
        self.labels: list[str] = []
        self.markdown = ""
        self.confluence_body = ""

        if not self._parse_file():
            raise ValueError(f"Failed to parse Markdown file: {file_path}")

    def _parse_file(self) -> bool:
        try:
            with open(self.file_path, encoding="utf-8") as f:
                self.markdown = f.read()
        except FileNotFoundError:
            print(f"File not found: {self.file_path}")  # noqa: T201
            return False

        match = re.match(r"^---\n(.*?)\n---", self.markdown, re.DOTALL)
        if match:
            yaml_block = match.group(1)
            self.markdown = self.markdown.replace(yaml_block, "")
            try:
                metadata = yaml.safe_load(yaml_block) or {}
            except yaml.YAMLError as exc:
                print(f"Error parsing YAML front-matter: {exc}")  # noqa: T201
                return False

            for k, v in metadata.items():
                if k in ("title", "space", "parent_title", "parent_id", "labels"):
                    setattr(self, k, v)
                elif k == "page-properties":
                    self.page_properties = v or {}
        else:
            print(f"No YAML front-matter found in {self.file_path}")  # noqa: T201

        self._collect_image_attachments()
        self._apply_confluence_link_replacements()
        self._render_confluence_body()
        self._prepend_page_properties_macro()
        return True

    def _prepend_page_properties_macro(self) -> None:
        """Prepend a Confluence Page Properties macro if ``page-properties`` was set."""
        if not self.page_properties:
            return

        doc_status = self.page_properties.get("document_status", "DRAFT")
        if doc_status == "PUBLISHED":
            status_colour = "Green"
        elif doc_status == "DRAFT":
            status_colour = "Yellow"
        else:
            status_colour = "Red"

        macro = (
            '<ac:structured-macro ac:name="details">'
            "<ac:rich-text-body><table><tbody>"
            f"<tr><th>Description</th><td>{self.page_properties.get('description', '')}</td></tr>"
            f"<tr><th>Created By</th><td>{self.page_properties.get('created_by', '')}</td></tr>"
            f"<tr><th>Version</th><td>{self.page_properties.get('version', '0.1')}</td></tr>"
            "<tr><th>Document Status</th><td>"
            '<ac:structured-macro ac:name="status">'
            f'<ac:parameter ac:name="title">{doc_status}</ac:parameter>'
            f'<ac:parameter ac:name="colour">{status_colour}</ac:parameter>'
            "</ac:structured-macro>"
            "</td></tr>"
            "</tbody></table></ac:rich-text-body>"
            "</ac:structured-macro>"
        )
        self.confluence_body = macro + self.confluence_body

    def _collect_image_attachments(self) -> None:
        """Find local image references and add them to the attachments list."""
        for image_path in re.findall(r"!\[.*?\]\((.*?)\)", self.markdown):
            if not image_path.startswith("http"):
                abs_path = os.path.abspath(os.path.join(os.path.dirname(self.file_path), image_path))
                self.attachments.append(abs_path)

    def _apply_confluence_link_replacements(self) -> None:
        """
        Replace annotated Markdown links with Confluence internal page links.

        A link annotated with ``<!-- replace_link(<page_id>) -->`` is rewritten
        to a Confluence-style URL::

            [My Link](./some-file.md) <!-- replace_link(98765) -->
        """
        pattern = r"(?<!\!)\[([^\]]+)\]\([^\)]+\)\s*<!--\s*replace_link\(([0-9]*)\)\s*-->"

        def _replace(m: re.Match) -> str:
            title, page_id = m.group(1), m.group(2)
            print(f"  Replaced link: '{title}' \u2192 Confluence page ID {page_id}")  # noqa: T201
            return f"[{title}](/spaces/{self.space}/pages/{page_id})"

        self.markdown = re.sub(pattern, _replace, self.markdown)

    def _render_confluence_body(self) -> None:
        renderer = ConfluenceRenderer(use_xhtml=True)
        md = mistune.Markdown(renderer=renderer)
        self.confluence_body = md(self.markdown)

    @property
    def valid(self) -> bool:
        """Return True if the file has the minimum required fields to be published."""
        if not self.title or not self.space:
            return False
        if not self.parent_id and not self.parent_title:
            return False
        return len(self.markdown) >= 1


class ConfluenceUpdater:
    """
    Creates and updates Confluence pages from Markdown files.

    Parameters
    ----------
    confluence_url:
        Base URL of your Confluence instance (e.g. ``https://wiki.example.com``).
    confluence_token:
        Personal Access Token for authentication.

    """

    def __init__(self, confluence_url: str, confluence_token: str) -> None:
        self.confluence_url = confluence_url
        self.confluence_token = confluence_token
        self._api = MinimalConfluence(
            host=self.confluence_url + "/rest/api",
            token=self.confluence_token,
        )
        self._api_full = Confluence(url=self.confluence_url, token=self.confluence_token)
        self._doc_args: dict = {}

    # ── Public methods ────────────────────────────────────────────────────────

    def publish_file(self, file_path: str) -> None:
        """Publish a single Markdown file to Confluence."""
        md = ConfluenceMarkdownFile(file_path=file_path, **self._doc_args)
        if not md.valid:
            print(f"Skipping {file_path} \u2014 failed validation (missing title, space, or parent).")  # noqa: T201
            return
        self._upsert_page(md)

    def publish_directory(self, dir_path: str) -> None:
        """Publish all ``.md`` files in *dir_path* to Confluence."""
        for md_file in self._list_files(dir_path, ext="md"):
            self.publish_file(file_path=md_file)

    def process_repo_tree(self, dir_path: str) -> None:
        """
        Scan *dir_path* for subdirectories that contain a ``confluence.yml`` and publish each.

        For each repository found, an index page is created (or updated) in
        Confluence and all Markdown files under ``repo-docs-path`` are
        published as children of that index page.
        """
        for repo_path in self._list_dirs(dir_path, require_confluence_yml=True):
            config = ConfluenceRepoConfig(repo_path=repo_path)
            if not config.valid:
                continue

            result = self._ensure_index_page(
                parent_id=config.parent_id,
                title=config.directory_title,
            )
            if result:
                self._doc_args["parent_id"] = result.get("id")
                self._doc_args["space"] = config.space
                self.publish_directory(config.docs_path)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _list_files(self, dir_path: str, ext: str) -> list[str]:
        return [os.path.join(dir_path, f) for f in os.listdir(dir_path) if f.endswith("." + ext)]

    def _list_dirs(self, dir_path: str, require_confluence_yml: bool = False) -> list[str]:
        result = []
        for item in os.listdir(dir_path):
            item_path = os.path.join(dir_path, item)
            if not os.path.isdir(item_path):
                continue
            if require_confluence_yml and not os.path.exists(os.path.join(item_path, "confluence.yml")):
                continue
            result.append(item_path)
        return result

    def _ensure_index_page(self, parent_id: str, title: str) -> Any:
        return self._api_full.update_or_create(parent_id=parent_id, title=title, body="Index")

    def _get_page(self, space: str, title: str) -> Any:
        return self._api.get_page(space_key=space, title=title)

    def _page_exists(self, space: str, title: str) -> bool:
        return bool(self._api.get_page(space_key=space, title=title))

    def _upsert_page(self, md: ConfluenceMarkdownFile) -> None:
        # md.space and md.title are guaranteed non-None — _upsert_page is only
        # ever called after the md.valid property has been checked.
        space: str = md.space  # type: ignore[assignment]
        title: str = md.title  # type: ignore[assignment]

        if self._page_exists(space=space, title=title):
            page = self._get_page(space=space, title=title)
            self._api.update_page(page, body=md.confluence_body, labels=md.labels)
            print(f"\u2713  Updated  '{title}'")  # noqa: T201
        else:
            if not md.parent_id:
                parent = self._get_page(space=space, title=md.parent_title)  # type: ignore[arg-type]
                md.parent_id = parent["id"] if parent and "id" in parent else None
            if not md.parent_id:
                raise RuntimeError(f"Could not resolve parent page for '{title}'")
            self._api.create_page(
                space=space,
                title=title,
                parent_id=md.parent_id,
                body=md.confluence_body,
                labels=md.labels,
            )
            print(f"\u2713  Created  '{title}'")  # noqa: T201

        # Upload local image attachments
        page = self._get_page(space=space, title=title)
        for attachment_path in md.attachments:
            filename = os.path.basename(attachment_path)
            mimetype = mimetypes.guess_type(attachment_path)[0] or "application/octet-stream"
            self._api_full.attach_file(
                attachment_path,
                name=filename,
                content_type=mimetype,
                page_id=page["id"],
            )
            print(f"  \u21b3  Attached '{filename}'")  # noqa: T201
