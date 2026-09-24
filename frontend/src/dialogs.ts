// Replaces the project-navigation-dropdown and footer-user-menu Stimulus
// controllers: <button data-dialog-open="id"> opens <dialog id>, clicking the
// backdrop or [data-dialog-close] closes it, and focus returns to the trigger.

function triggerFor(dialog: HTMLDialogElement): HTMLElement | null {
  return document.querySelector<HTMLElement>(`[data-dialog-open="${dialog.id}"]`)
}

export function installDialogs(): void {
  // HTMX fragments swapped into #modal-body open the shared dialog.
  document.addEventListener("htmx:afterSwap", (event) => {
    const target = (event as CustomEvent<{ target: Element }>).detail.target
    const dialog = document.getElementById("modal")
    if (target.id === "modal-body" && dialog instanceof HTMLDialogElement && !dialog.open) {
      dialog.showModal()
    }
  })

  document.addEventListener("click", (event) => {
    const target = event.target
    if (!(target instanceof Element)) return

    const opener = target.closest<HTMLElement>("[data-dialog-open]")
    if (opener) {
      const dialog = document.getElementById(opener.dataset["dialogOpen"] ?? "")
      if (dialog instanceof HTMLDialogElement && !dialog.open) {
        opener.setAttribute("aria-expanded", "true")
        dialog.showModal()
      }
      return
    }

    const closer = target.closest("[data-dialog-close]")
    const dialog = target.closest("dialog")
    if (closer && dialog instanceof HTMLDialogElement) {
      dialog.close()
      return
    }

    // A click on the ::backdrop lands on the <dialog> element itself.
    if (target instanceof HTMLDialogElement && target.open) target.close()
  })

  document.addEventListener(
    "close",
    (event) => {
      const dialog = event.target
      if (!(dialog instanceof HTMLDialogElement)) return
      const trigger = triggerFor(dialog)
      trigger?.setAttribute("aria-expanded", "false")
      trigger?.focus()
    },
    true,
  )
}
