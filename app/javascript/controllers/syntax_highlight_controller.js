import {Controller} from "@hotwired/stimulus"

import hljs from "@highlightjs/cdn-assets/es/core.min.js";
import javascript from "@highlightjs/cdn-assets/es/languages/javascript.min.js";
import python from "@highlightjs/cdn-assets/es/languages/python.min.js";
import ruby from "@highlightjs/cdn-assets/es/languages/ruby.min.js";
import css from "@highlightjs/cdn-assets/es/languages/css.min.js";
import xml from "@highlightjs/cdn-assets/es/languages/xml.min.js";

export default class extends Controller {
  async initialize() {
    // xml also includes html. If it's registered after the css language
    // highlightjs seems to overeagerly infer code as css rather than html.
    // Registering it before doesn't seem to cause the same issue.
    hljs.registerLanguage("xml", xml);
    hljs.registerLanguage("css", css);
    hljs.registerLanguage("javascript", javascript);
    hljs.registerLanguage("ruby", ruby);
    hljs.registerLanguage("python", python);
  }

  async connect() {
    for (const element of this.element.querySelectorAll("pre")) {
      hljs.highlightElement(element);
    }
  }
}
