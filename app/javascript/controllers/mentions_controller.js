import { Controller } from "@hotwired/stimulus";
import Tribute from "tributejs";
import { get } from "@rails/request.js";

export default class extends Controller {
  static targets = ["input"];
  static values = { url: String };

  connect() {
    this.inputTarget.addEventListener("trix-initialize", (event) => {
      this.editor = event.target.editor;
      this.setupTribute();
    });
  }

  setupTribute() {
    this.tribute = new Tribute({
      collection: [
        {
          trigger: "@",
          allowSpaces: true,
          lookup: "key",
          menuShowMinLength: 1,
          values: this.fetchUsers,
          selectTemplate: () => "", // manual
          menuItemTemplate: (item) => `@${item.original.key}`,
          menuItemLimit: 10,
        },
      ],
      menuContainer: document.body // optional: helps if the input is inside modals/scroll containers
    });

    this.tribute.attach(this.inputTarget);
    this.inputTarget.addEventListener("tribute-replaced", this.replaced);
    this.tribute.range.pasteHtml = this._pasteHtml.bind(this);
  }

   replaced(event) {
    let mention = event.detail.item.original
    console.log("Replaced with mention:", mention);

    let attachment = new Trix.Attachment({
      content: mention.content,
      sgid: mention.value
    })
    this.editor.insertAttachment(attachment)
    this.editor.insertString(" ")
  }

   _pasteHtml(html, startPos, endPos) {
     let range = this.editor.getSelectedRange()
     let position = range[0]
     let length = endPos - startPos

     this.editor.setSelectedRange([position - length, position])
     this.editor.deleteInDirection("backward")
   }

  fetchUsers = (text, callback) => {
    fetch(`${this.urlValue}?query=${text}`)
      .then(response => response.json())
      .then(users => callback(users))
      .catch(error => callback([]));
  }
}
