// htmx extensions (ws, Idiomorph's morph) register themselves on a global
// `htmx`, so expose the bundled instance before they are imported.
import htmx from "htmx.org"

declare global {
  interface Window {
    htmx: typeof htmx
  }
}

window.htmx = htmx

export default htmx
