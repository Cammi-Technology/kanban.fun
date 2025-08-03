import { Controller } from "@hotwired/stimulus";
import Tribute from "tributejs";
import { get } from "@rails/request.js";

export default class extends Controller {
  static targets = ["input"]
  static values = {
    url: String,
  }

  connect() {
    console.log(this.urlValue);
  }

  disconnect() {
    this.tribute.detach(this.inputTarget);
  }

  inputTargetConnected() {
    this.tribute = new Tribute({
      values: async (text, cb) => {
          const response = await get(`${this.urlValue}?query=${text}`); 
          if (response.ok) {
            const account_users = await response.json;
            cb(account_users.map(user => ({ key: user.name, value: user.attachable_sgid })));
          }
      },
      selectTemplate: function (item) {
        return `@${item.original.value}`;
      },
    });
    this.tribute.attach(this.inputTarget);
  }
}
