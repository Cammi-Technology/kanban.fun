# Pin npm packages by running ./bin/importmap

pin "application"

pin "trix"
pin "@rails/actiontext", to: "actiontext.esm.js"

pin "@hotwired/turbo-rails", to: "turbo.min.js"

pin "@hotwired/stimulus", to: "stimulus.min.js"
pin "@hotwired/stimulus-loading", to: "stimulus-loading.js"

pin "@rails/request.js", to: "@rails--request.js.js" # @0.0.12

pin "tributejs" # @5.1.3

pin_all_from "app/javascript/controllers", under: "controllers"
