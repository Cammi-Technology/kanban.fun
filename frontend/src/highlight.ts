// Syntax highlighting for code blocks (the syntax-highlight controller).
import hljs from "highlight.js/lib/core"
import bash from "highlight.js/lib/languages/bash"
import css from "highlight.js/lib/languages/css"
import javascript from "highlight.js/lib/languages/javascript"
import json from "highlight.js/lib/languages/json"
import python from "highlight.js/lib/languages/python"
import ruby from "highlight.js/lib/languages/ruby"
import sql from "highlight.js/lib/languages/sql"
import typescript from "highlight.js/lib/languages/typescript"
import xml from "highlight.js/lib/languages/xml"

// xml (which covers html) first: registered after css, highlight.js tends to
// infer html as css.
hljs.registerLanguage("xml", xml)
hljs.registerLanguage("html", xml)
hljs.registerLanguage("css", css)
hljs.registerLanguage("javascript", javascript)
hljs.registerLanguage("typescript", typescript)
hljs.registerLanguage("ruby", ruby)
hljs.registerLanguage("python", python)
hljs.registerLanguage("bash", bash)
hljs.registerLanguage("json", json)
hljs.registerLanguage("sql", sql)
hljs.configure({ ignoreUnescapedHTML: true })

export function highlightWithin(root: ParentNode): void {
  root.querySelectorAll<HTMLElement>("[data-highlight] pre code").forEach((block) => {
    if (block.dataset["highlighted"] === "yes") return
    hljs.highlightElement(block)
  })
}
