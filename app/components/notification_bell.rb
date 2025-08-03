# frozen_string_literal: true

class Components::NotificationBell < Components::Base
  def view_template
    span(
      data_controller: "kanban--notifications",
      data_kanban__notifications_subscriptions_url_value: web_push_subscriptions_path
    ) do
      button(
        data_kanban__notifications_target: "subscribeButton",
        class: "w-8 h-8",
        data_action: "kanban--notifications#subscribe"
      ) do
        plain "foo"
        Tabler::Bell(variant: :outline)
        Tabler::BellExclamation(variant: :outline, hidden: true)
      end

      not_allowed_dialog
    end
  end

  def not_allowed_dialog
    dialog(
      data_kanban__notifications_target: "notAllowedNotice",
      class: "dialog"
    ) do
      div(class: "flex flex-col text-center") do
        whitespace
        span(class: "btn text-4xl") do
          Tabler::BellExclamation(variant: :outline, aria: { hidden: "true" })
          span(class: "sr-only") { "Notifications alert" }
        end
        section do
          h1(class: "text-xl") { "Notifications aren’t allowed" }
          div(class: "txt-align-start margin-block-start") do
            # render partial: "pwa/browser_settings"
            # render partial: "pwa/system_settings"
            # render partial: "pwa/install_instructions"
          end
        end
        form(method: "dialog", class: "flex align-center gap center") do
          button(class: "btn dialog__close", autofocus: "true") do
            span(class: "for-screen-reader") { "Close" }
            Remix::CloseCircleFill(aria: { hidden: "true" })
          end
        end
      end
    end
  end
end
