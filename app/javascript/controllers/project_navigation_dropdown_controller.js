import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["dialog", "trigger"]

  open() {
    if (!this.hasDialogTarget || !this.dialogTarget.showModal) return

    this.triggerTarget.setAttribute("aria-expanded", "true")
    this.dialogTarget.showModal()
  }

  close() {
    if (this.hasDialogTarget && this.dialogTarget.open) this.dialogTarget.close()
  }

  cancel(event) {
    event.preventDefault()
    this.close()
  }

  closed() {
    if (this.hasTriggerTarget) {
      this.triggerTarget.setAttribute("aria-expanded", "false")
      this.triggerTarget.focus()
    }
  }

  backdropClose(event) {
    if (event.target === this.dialogTarget) this.close()
  }
}
