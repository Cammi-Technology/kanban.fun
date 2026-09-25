// Tiptap rich-text editing with @mentions (replaces Trix + Tribute.js).
//
// Markup rendered by the server (kanban/projects/components.py):
//
//   <div data-rich-text data-mention-url="…" data-initial='{"type":"doc",…}'>
//     <textarea name="content">plain text</textarea>
//   </div>
//
// Without JavaScript the textarea is submitted as plain text. With it, the
// editor mounts, the textarea is hidden and kept in sync with the editor's
// JSON, and a hidden content_format=tiptap input tells the server to parse
// JSON. The server re-validates every mention against account membership.

import { Editor, type JSONContent } from "@tiptap/core"
import Mention from "@tiptap/extension-mention"
import StarterKit from "@tiptap/starter-kit"
import type { SuggestionKeyDownProps, SuggestionProps } from "@tiptap/suggestion"

export interface MemberSuggestion {
  id: string
  label: string
}

const editors = new WeakMap<HTMLElement, Editor>()

async function fetchMembers(url: string, query: string): Promise<MemberSuggestion[]> {
  const response = await fetch(`${url}?q=${encodeURIComponent(query)}`, {
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  })
  if (!response.ok) return []
  return (await response.json()) as MemberSuggestion[]
}

class SuggestionMenu {
  private readonly element: HTMLUListElement
  private items: MemberSuggestion[] = []
  private selected = 0
  private command: ((item: MemberSuggestion) => void) | null = null

  constructor() {
    this.element = document.createElement("ul")
    this.element.className = "mention-menu"
    this.element.setAttribute("role", "listbox")
    this.element.addEventListener("mousedown", (event) => {
      const option = (event.target as Element).closest<HTMLElement>("[data-index]")
      if (!option) return
      event.preventDefault()
      this.choose(Number(option.dataset["index"]))
    })
    document.body.append(this.element)
  }

  update(props: SuggestionProps<MemberSuggestion, MemberSuggestion>): void {
    this.items = props.items
    this.command = (item) => props.command(item)
    this.selected = 0
    this.render()
    const rect = props.clientRect?.()
    if (rect) {
      this.element.style.left = `${rect.left + window.scrollX}px`
      this.element.style.top = `${rect.bottom + window.scrollY + 4}px`
    }
  }

  keyDown({ event }: SuggestionKeyDownProps): boolean {
    if (!this.items.length) return false
    if (event.key === "ArrowDown") {
      this.selected = (this.selected + 1) % this.items.length
    } else if (event.key === "ArrowUp") {
      this.selected = (this.selected + this.items.length - 1) % this.items.length
    } else if (event.key === "Enter" || event.key === "Tab") {
      this.choose(this.selected)
      return true
    } else {
      return false
    }
    this.render()
    return true
  }

  destroy(): void {
    this.element.remove()
  }

  private choose(index: number): void {
    const item = this.items[index]
    if (item && this.command) this.command(item)
  }

  private render(): void {
    this.element.replaceChildren(
      ...this.items.map((item, index) => {
        const option = document.createElement("li")
        option.dataset["index"] = String(index)
        option.setAttribute("role", "option")
        option.setAttribute("aria-selected", String(index === this.selected))
        option.className = index === this.selected ? "mention-menu__item is-selected" : "mention-menu__item"
        option.textContent = `@${item.label}`
        return option
      }),
    )
    this.element.hidden = this.items.length === 0
  }
}

function parseInitial(raw: string | undefined): JSONContent {
  try {
    const parsed = JSON.parse(raw ?? "") as JSONContent
    return parsed.type === "doc" ? parsed : { type: "doc", content: [] }
  } catch {
    return { type: "doc", content: [] }
  }
}

export function mountEditor(root: HTMLElement): Editor | null {
  if (editors.has(root)) return editors.get(root) ?? null
  const textarea = root.querySelector<HTMLTextAreaElement>("textarea")
  if (!textarea) return null
  const mentionUrl = root.dataset["mentionUrl"] ?? ""

  const format = document.createElement("input")
  format.type = "hidden"
  format.name = "content_format"
  format.value = "tiptap"

  const mount = document.createElement("div")
  mount.className = "rich-text__editor"

  const sync = (editor: Editor): void => {
    textarea.value = editor.isEmpty ? "" : JSON.stringify(editor.getJSON())
  }

  const editor = new Editor({
    element: mount,
    content: parseInitial(root.dataset["initial"]),
    editorProps: {
      attributes: {
        class: "rich-content rich-text__surface",
        role: "textbox",
        "aria-multiline": "true",
        "aria-label": textarea.labels?.[0]?.textContent ?? "Content",
        "data-placeholder": root.dataset["placeholder"] ?? "",
      },
    },
    extensions: [
      StarterKit.configure({
        heading: { levels: [2, 3, 4] },
        underline: false,
        link: { openOnClick: false, autolink: true, protocols: ["http", "https", "mailto"] },
      }),
      Mention.configure({
        HTMLAttributes: { class: "mention" },
        renderText: ({ node }) => `@${String(node.attrs["label"] ?? "")}`,
        suggestion: {
          char: "@",
          allowSpaces: true,
          items: async ({ query }) => fetchMembers(mentionUrl, query),
          render: () => {
            let menu: SuggestionMenu | null = null
            return {
              onStart: (props) => {
                menu = new SuggestionMenu()
                menu.update(props)
              },
              onUpdate: (props) => menu?.update(props),
              onKeyDown: (props) => {
                if (props.event.key === "Escape") {
                  menu?.destroy()
                  menu = null
                  return true
                }
                return menu?.keyDown(props) ?? false
              },
              onExit: () => {
                menu?.destroy()
                menu = null
              },
            }
          },
        },
      }),
    ],
    onUpdate: ({ editor: current }) => sync(current),
    onCreate: ({ editor: current }) => sync(current),
  })

  textarea.hidden = true
  textarea.required = false
  root.append(format, mount)
  root.classList.add("rich-text--mounted")

  // Empty rich text can't use the textarea's `required`, so check on submit.
  textarea.form?.addEventListener("submit", (event) => {
    sync(editor)
    if (root.querySelector("textarea")?.dataset["required"] === "true" && editor.isEmpty) {
      event.preventDefault()
      mount.querySelector<HTMLElement>("[contenteditable]")?.focus()
    }
  })
  if (textarea.hasAttribute("required")) textarea.dataset["required"] = "true"

  editors.set(root, editor)
  return editor
}

export function mountEditorsWithin(root: ParentNode): void {
  root.querySelectorAll<HTMLElement>("[data-rich-text]").forEach((element) => {
    mountEditor(element)
  })
}

export function destroyEditorsWithin(root: ParentNode): void {
  root.querySelectorAll<HTMLElement>("[data-rich-text]").forEach((element) => {
    editors.get(element)?.destroy()
    editors.delete(element)
  })
}
