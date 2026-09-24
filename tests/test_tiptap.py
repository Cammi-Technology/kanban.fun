"""Tiptap JSON: sanitising, rendering, mention extraction, plain text."""

from __future__ import annotations

from htpy import fragment

from kanban.core import tiptap


def render(doc: tiptap.Doc) -> str:
    return str(fragment[tiptap.render(doc, lambda mention_id: f"/m/{mention_id}")])


def test_sanitize_drops_unknown_nodes_marks_and_attrs() -> None:
    dirty = {
        "type": "doc",
        "content": [
            {"type": "iframe", "attrs": {"src": "https://evil"}},
            {
                "type": "paragraph",
                "attrs": {"onclick": "x"},
                "content": [
                    {
                        "type": "text",
                        "text": "hi",
                        "marks": [{"type": "bold"}, {"type": "underline"}],
                    },
                    {
                        "type": "text",
                        "text": "link",
                        "marks": [
                            {"type": "link", "attrs": {"href": "javascript:alert(1)"}}
                        ],
                    },
                ],
            },
            {
                "type": "heading",
                "attrs": {"level": 1},
                "content": [{"type": "text", "text": "H"}],
            },
        ],
    }
    clean = tiptap.sanitize(dirty)
    assert clean == {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "hi", "marks": [{"type": "bold"}]},
                    {"type": "text", "text": "link"},
                ],
            },
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "H"}],
            },
        ],
    }


def test_sanitize_rejects_non_documents() -> None:
    assert tiptap.sanitize("nope") == tiptap.empty_doc()
    assert tiptap.sanitize({"type": "paragraph"}) == tiptap.empty_doc()


def test_render_escapes_and_links_mentions() -> None:
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "<img src=x onerror=alert(1)>"},
                    {"type": "mention", "attrs": {"id": "42", "label": "Rachel Jones"}},
                    {
                        "type": "text",
                        "text": "site",
                        "marks": [
                            {"type": "link", "attrs": {"href": "https://kanban.fun"}}
                        ],
                    },
                ],
            }
        ],
    }
    html = render(doc)
    assert "&lt;img src=x onerror=alert(1)&gt;" in html
    assert (
        '<a class="mention" href="/m/42" data-mention-id="42">@Rachel Jones</a>' in html
    )
    assert (
        '<a href="https://kanban.fun" rel="noopener noreferrer nofollow">site</a>'
        in html
    )


def test_code_block_language_is_whitelisted() -> None:
    doc = tiptap.sanitize(
        {
            "type": "doc",
            "content": [
                {
                    "type": "codeBlock",
                    "attrs": {"language": "python"},
                    "content": [{"type": "text", "text": "x = 1"}],
                },
                {
                    "type": "codeBlock",
                    "attrs": {"language": '"><script>'},
                    "content": [{"type": "text", "text": "y"}],
                },
            ],
        }
    )
    html = render(doc)
    assert '<pre><code class="language-python">x = 1</code></pre>' in html
    assert "<pre><code>y</code></pre>" in html


def test_mention_ids_and_plain_text() -> None:
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Hi "},
                    {"type": "mention", "attrs": {"id": "7", "label": "Sam"}},
                ],
            },
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "mention",
                                        "attrs": {"id": "7", "label": "Sam"},
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
        ],
    }
    assert tiptap.mention_ids(doc) == [7]
    assert tiptap.plain_text(doc) == "Hi @Sam\n@Sam"


def test_parse_submission_plain_text_fallback() -> None:
    doc = tiptap.parse_submission("One\ntwo\n\nThree", "")
    assert tiptap.plain_text(doc) == "One\ntwo\nThree"
    assert tiptap.parse_submission("{not json", "tiptap") == tiptap.empty_doc()


def test_rewrite_mentions_unknown_becomes_text() -> None:
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "mention", "attrs": {"id": "9", "label": "Ghost"}}
                ],
            }
        ],
    }
    assert tiptap.rewrite_mentions(doc, {})["content"][0]["content"] == [
        {"type": "text", "text": "@Ghost"}
    ]
