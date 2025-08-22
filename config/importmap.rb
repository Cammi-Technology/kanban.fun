# Pin npm packages by running ./bin/importmap

pin "application"

pin "trix"
pin "@rails/actiontext", to: "actiontext.esm.js"

pin "@hotwired/turbo-rails", to: "turbo.min.js"

pin "@hotwired/stimulus", to: "stimulus.min.js"
pin "@hotwired/stimulus-loading", to: "stimulus-loading.js"

pin "@rails/request.js", to: "@rails--request.js.js" # @0.0.12

pin "tributejs" # @5.1.3

pin "@highlightjs/cdn-assets/es/core.min.js", to: "@highlightjs--cdn-assets--es--core.min.js.js" # @11.11.1
pin "@highlightjs/cdn-assets/es/languages/css.min.js", to: "@highlightjs--cdn-assets--es--languages--css.min.js.js" # @11.11.1
pin "@highlightjs/cdn-assets/es/languages/javascript.min.js", to: "@highlightjs--cdn-assets--es--languages--javascript.min.js.js" # @11.11.1
pin "@highlightjs/cdn-assets/es/languages/python.min.js", to: "@highlightjs--cdn-assets--es--languages--python.min.js.js" # @11.11.1
pin "@highlightjs/cdn-assets/es/languages/ruby.min.js", to: "@highlightjs--cdn-assets--es--languages--ruby.min.js.js" # @11.11.1
pin "@highlightjs/cdn-assets/es/languages/xml.min.js", to: "@highlightjs--cdn-assets--es--languages--xml.min.js.js" # @11.11.1

pin_all_from "app/javascript/controllers", under: "controllers"
