// Browser entry point: HTMX + WebSocket extension + Idiomorph, Tiptap
// editors, dialogs, syntax highlighting and Web Push.
import htmx from "./htmx-global"
import "htmx-ext-ws"
import "idiomorph/htmx"

import { installCable } from "./cable"
import { installDialogs } from "./dialogs"
import { mountEditorsWithin } from "./editor"
import { highlightWithin } from "./highlight"
import { installPush } from "./push"

htmx.config.responseHandling = [
  { code: "204", swap: false },
  { code: "[23]..", swap: true },
  // Validation errors come back as a form fragment with HTTP 422.
  { code: "422", swap: true, error: false },
  { code: "[45]..", swap: false, error: true },
]
htmx.config.historyCacheSize = 0

function enhance(root: ParentNode): void {
  mountEditorsWithin(root)
  highlightWithin(root)
}

htmx.onLoad((element) => {
  if (element instanceof Element) enhance(element)
})

// Idiomorph keeps existing nodes, so re-run enhancements after every morph.
document.addEventListener("htmx:afterSettle", (event) => {
  const target = (event as CustomEvent<{ elt: Element }>).detail.elt
  if (target instanceof Element) enhance(target)
})
document.addEventListener("htmx:oobAfterSwap", (event) => {
  const target = (event as CustomEvent<{ target: Element }>).detail.target
  if (target instanceof Element) enhance(target)
})

installDialogs()
installCable()
installPush()
enhance(document)
