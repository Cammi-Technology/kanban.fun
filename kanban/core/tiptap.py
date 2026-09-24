"""Tiptap (ProseMirror) JSON documents: sanitising, rendering and mentions.

Browser-submitted JSON is never trusted. ``sanitize`` rebuilds a document
using only the node types, marks and attributes the editor is configured
with; ``render`` turns that document into escaped HTML with htpy.
Mention nodes are validated separately against account membership, see
``kanban.projects.mentions``.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator, Mapping
from typing import Any, Final
from urllib.parse import urlparse

from htpy import (
    Element,
    Node,
    a,
    blockquote,
    br,
    code,
    em,
    h2,
    h3,
    h4,
    hr,
    li,
    ol,
    p,
    pre,
    s,
    span,
    strong,
    ul,
)

type Doc = dict[str, Any]
type MentionLink = Callable[[str], str | None]

BLOCK_TYPES: Final = {
    "paragraph",
    "heading",
    "bulletList",
    "orderedList",
    "listItem",
    "blockquote",
    "codeBlock",
    "horizontalRule",
}
INLINE_TYPES: Final = {"text", "hardBreak", "mention"}
MARK_TYPES: Final = {"bold", "italic", "strike", "code", "link"}
CODE_LANGUAGES: Final = {
    "javascript",
    "typescript",
    "python",
    "ruby",
    "css",
    "html",
    "xml",
    "bash",
    "json",
    "sql",
    "plaintext",
}
SAFE_LINK_SCHEMES: Final = {"http", "https", "mailto"}
MAX_DEPTH: Final = 20
MAX_TEXT: Final = 100_000


def empty_doc() -> Doc:
    return {"type": "doc", "content": []}


def from_plain_text(text: str) -> Doc:
    """Build a document from textarea input (the no-JavaScript fallback)."""
    paragraphs = [chunk.strip() for chunk in text.replace("\r\n", "\n").split("\n\n")]
    content: list[Doc] = []
    for chunk in paragraphs:
        if not chunk:
            continue
        inline: list[Doc] = []
        for index, line in enumerate(chunk.split("\n")):
            if index:
                inline.append({"type": "hardBreak"})
            if line:
                inline.append({"type": "text", "text": line})
        content.append({"type": "paragraph", "content": inline})
    return {"type": "doc", "content": content}


def parse_submission(raw: str, content_format: str) -> Doc:
    """Turn a form submission into a sanitised document.

    The Tiptap editor submits JSON and sets ``content_format=tiptap``; without
    JavaScript the same field is a plain textarea.
    """
    if content_format == "tiptap":
        try:
            data = json.loads(raw) if raw else empty_doc()
        except ValueError:
            return empty_doc()
        return sanitize(data)
    return from_plain_text(raw)


def _safe_href(href: object) -> str | None:
    if not isinstance(href, str) or len(href) > 2000:
        return None
    parsed = urlparse(href.strip())
    if parsed.scheme.lower() not in SAFE_LINK_SCHEMES:
        return None
    return href.strip()


def _clean_marks(marks: object) -> list[Doc]:
    cleaned: list[Doc] = []
    if not isinstance(marks, list):
        return cleaned
    for mark in marks:
        if not isinstance(mark, Mapping) or mark.get("type") not in MARK_TYPES:
            continue
        if mark["type"] == "link":
            attrs = mark.get("attrs")
            href = _safe_href(attrs.get("href") if isinstance(attrs, Mapping) else None)
            if href is None:
                continue
            cleaned.append({"type": "link", "attrs": {"href": href}})
        else:
            cleaned.append({"type": str(mark["type"])})
    return cleaned


def _clean_node(node: object, depth: int) -> Doc | None:  # noqa: PLR0912
    if depth > MAX_DEPTH or not isinstance(node, Mapping):
        return None
    node_type = node.get("type")
    if node_type == "text":
        text = node.get("text")
        if not isinstance(text, str) or not text:
            return None
        cleaned: Doc = {"type": "text", "text": text[:MAX_TEXT]}
        marks = _clean_marks(node.get("marks"))
        if marks:
            cleaned["marks"] = marks
        return cleaned
    if node_type == "hardBreak":
        return {"type": "hardBreak"}
    if node_type == "horizontalRule":
        return {"type": "horizontalRule"}
    if node_type == "mention":
        attrs = node.get("attrs")
        if not isinstance(attrs, Mapping):
            return None
        mention_id = attrs.get("id")
        label = attrs.get("label")
        if not isinstance(mention_id, (str, int)) or not str(mention_id).isdigit():
            return None
        return {
            "type": "mention",
            "attrs": {
                "id": str(mention_id),
                "label": str(label)[:200] if label else "",
            },
        }
    if node_type not in BLOCK_TYPES:
        return None
    result: Doc = {"type": node_type}
    attrs = node.get("attrs")
    if node_type == "heading":
        level = attrs.get("level") if isinstance(attrs, Mapping) else None
        level = level if level in (2, 3, 4) else 2
        result["attrs"] = {"level": level}
    elif node_type == "codeBlock":
        language = attrs.get("language") if isinstance(attrs, Mapping) else None
        result["attrs"] = {"language": language if language in CODE_LANGUAGES else None}
    elif node_type == "orderedList":
        start = attrs.get("start") if isinstance(attrs, Mapping) else None
        result["attrs"] = {"start": start if isinstance(start, int) else 1}
    children = node.get("content")
    if isinstance(children, list):
        cleaned_children = [
            child
            for child in (_clean_node(item, depth + 1) for item in children)
            if child is not None
        ]
        if node_type == "codeBlock":
            cleaned_children = [
                {"type": "text", "text": child["text"]}
                for child in cleaned_children
                if child["type"] == "text"
            ]
        if cleaned_children:
            result["content"] = cleaned_children
    return result


def sanitize(data: object) -> Doc:
    if not isinstance(data, Mapping) or data.get("type") != "doc":
        return empty_doc()
    content = data.get("content")
    if not isinstance(content, list):
        return empty_doc()
    blocks = [
        node
        for node in (_clean_node(item, 1) for item in content)
        if node is not None and node["type"] in BLOCK_TYPES
    ]
    return {"type": "doc", "content": blocks}


def walk(node: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    yield node
    for child in node.get("content", []) or []:
        if isinstance(child, Mapping):
            yield from walk(child)


def mention_ids(doc: Mapping[str, Any]) -> list[int]:
    seen: list[int] = []
    for node in walk(doc):
        if node.get("type") == "mention":
            raw = str(node.get("attrs", {}).get("id", ""))
            if raw.isdigit() and int(raw) not in seen:
                seen.append(int(raw))
    return seen


def plain_text(doc: Mapping[str, Any]) -> str:
    parts: list[str] = []

    def visit(node: Mapping[str, Any]) -> None:
        node_type = node.get("type")
        if node_type == "text":
            parts.append(str(node.get("text", "")))
        elif node_type == "mention":
            parts.append(f"@{node.get('attrs', {}).get('label', '')}")
        elif node_type == "hardBreak":
            parts.append("\n")
        for child in node.get("content", []) or []:
            if isinstance(child, Mapping):
                visit(child)
        if node_type in BLOCK_TYPES and node_type != "listItem":
            parts.append("\n")

    visit(doc)
    return "\n".join(line.strip() for line in "".join(parts).split("\n")).strip()


def rewrite_mentions(doc: Doc, labels: Mapping[int, str]) -> Doc:
    """Replace mention labels with canonical names; drop unknown mentions.

    ``labels`` maps valid AccountUser ids to their display names. A mention of
    anyone else becomes plain text so a forged id can never render as a link.
    """

    def fix(node: Doc) -> Doc:
        if node.get("type") == "mention":
            mention_id = int(node["attrs"]["id"])
            if mention_id in labels:
                return {
                    "type": "mention",
                    "attrs": {"id": str(mention_id), "label": labels[mention_id]},
                }
            label = node["attrs"].get("label") or "someone"
            return {"type": "text", "text": f"@{label}"}
        if "content" in node:
            return {**node, "content": [fix(child) for child in node["content"]]}
        return node

    return fix(doc)


def _render_text(node: Mapping[str, Any]) -> Node:
    rendered: Node = str(node.get("text", ""))
    for mark in node.get("marks", []) or []:
        mark_type = mark.get("type")
        if mark_type == "bold":
            rendered = strong[rendered]
        elif mark_type == "italic":
            rendered = em[rendered]
        elif mark_type == "strike":
            rendered = s[rendered]
        elif mark_type == "code":
            rendered = code[rendered]
        elif mark_type == "link":
            href = _safe_href(mark.get("attrs", {}).get("href"))
            if href:
                rendered = a(href=href, rel="noopener noreferrer nofollow")[rendered]
    return rendered


def _render_children(node: Mapping[str, Any], mention_link: MentionLink) -> list[Node]:
    return [
        _render_node(child, mention_link)
        for child in node.get("content", []) or []
        if isinstance(child, Mapping)
    ]


def _render_node(node: Mapping[str, Any], mention_link: MentionLink) -> Node:
    node_type = node.get("type")
    children = _render_children(node, mention_link)
    attrs = node.get("attrs") or {}
    match node_type:
        case "text":
            return _render_text(node)
        case "hardBreak":
            return br
        case "horizontalRule":
            return hr
        case "mention":
            mention_id = str(attrs.get("id", ""))
            label = f"@{attrs.get('label', '')}"
            href = mention_link(mention_id)
            if href is None:
                return label
            return a(".mention", href=href, data_mention_id=mention_id)[label]
        case "paragraph":
            return p[children]
        case "heading":
            heading: Element = {2: h2, 3: h3, 4: h4}.get(int(attrs.get("level", 2)), h2)
            return heading[children]
        case "bulletList":
            return ul[children]
        case "orderedList":
            start = attrs.get("start", 1)
            return ol(start=str(start) if start != 1 else None)[children]
        case "listItem":
            return li[children]
        case "blockquote":
            return blockquote[children]
        case "codeBlock":
            language = attrs.get("language")
            text = "".join(
                str(child.get("text", "")) for child in node.get("content", []) or []
            )
            css_class = f"language-{language}" if language else None
            return pre[code(class_=css_class)[text]]
    return span[children]


def render(doc: Mapping[str, Any], mention_link: MentionLink) -> list[Node]:
    """Render a sanitised document to htpy nodes."""
    return _render_children(doc, mention_link)
