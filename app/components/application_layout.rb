# frozen_string_literal: true

class Components::ApplicationLayout < Components::Base
  include Phlex::Rails::Helpers::ButtonTo
  include Phlex::Rails::Helpers::CSRFMetaTags
  include Phlex::Rails::Helpers::CSPMetaTag
  include Phlex::Rails::Helpers::JavascriptImportmapTags
  include Phlex::Rails::Helpers::StylesheetLinkTag

  prop :page_info, ::PageInfo, :positional, reader: :private

  def view_template(&)
    doctype
    html(lang: I18n.locale) do
      head do
        title { page_info.title }
        meta(name: "viewport", content: "width=device-width,initial-scale=1")
        meta(name: "apple-mobile-web-app-capable", content: "yes")
        meta(name: "mobile-web-app-capable", content: "yes")
        csrf_meta_tags
        csp_meta_tag

        link rel: "manifest", href: pwa_manifest_path(format: :json)
        meta name: "vapid-public-key", content: Rails.application.credentials.dig(:web_push, :public_key)

        link(rel: "icon", href: "/icon.png", type: "image/png")
        link(rel: "icon", href: "/icon.svg", type: "image/svg+xml")
        link(rel: "apple-touch-icon", href: "/icon.png")
        # Includes all stylesheet files in app/assets/stylesheets
        stylesheet_link_tag :app, "data-turbo-track": "reload"
        javascript_importmap_tags
      end
      body do
        if flash.present?
          if flash[:notice]
            plain flash[:notice]
          end

          if flash[:alert]
            plain flash[:alert]
          end
        end
        header(class: "app-shell__header") do
          if Current.account
            ProjectDropdown(projects: Current.account.projects)
          end
        end
        main(class: "app-shell__main") do
          yield
        end
        footer(class: "app-shell__footer") do
          if Current.user
            div(class: "app-shell__footer-user-menu", data: { controller: "footer-user-menu" }) do
              button(
                type: "button",
                class: "app-shell__footer-user-trigger",
                aria: { haspopup: "dialog", expanded: "false" },
                data: {
                  action: "footer-user-menu#open",
                  footer_user_menu_target: "trigger"
                }
              ) do
                Avatar(
                  name: Current.user.first_name.presence || Current.user.email,
                  size: :sm,
                  class: "app-shell__footer-avatar"
                )

                div(class: "app-shell__footer-user-meta") do
                  p(class: "app-shell__footer-user-name") do
                    plain Current.user.first_name.presence || Current.user.email
                  end
                  p(class: "app-shell__footer-user-email") { Current.user.email }
                end

                span(class: "app-shell__footer-user-trigger-icon", aria: { hidden: "true" }) do
                  Icon("bootstrap/chevron-down")
                end
              end

              dialog(
                class: "app-shell__footer-user-dialog",
                aria: { labelledby: "footer-user-menu-title" },
                data: {
                  action: "click->footer-user-menu#backdropClose cancel->footer-user-menu#cancel close->footer-user-menu#closed",
                  footer_user_menu_target: "dialog"
                }
              ) do
                div(class: "app-shell__footer-user-panel") do
                  div(class: "app-shell__footer-user-panel-header") do
                    h2(id: "footer-user-menu-title", class: "app-shell__footer-user-panel-title") do
                      plain Current.user.first_name.presence || Current.user.email
                    end
                    p(class: "app-shell__footer-user-panel-subtitle") { Current.user.email }
                  end

                  nav(aria: { label: "User menu" }, class: "app-shell__footer-user-panel-nav") do
                    a(href: accounts_path, class: "app-shell__footer-user-panel-link") { "Accounts" }
                    a(href: edit_identity_email_path, class: "app-shell__footer-user-panel-link") { "Email settings" }
                    a(href: edit_password_path, class: "app-shell__footer-user-panel-link") { "Password" }
                    a(href: sessions_path, class: "app-shell__footer-user-panel-link") { "Sessions" }
                  end

                  div(class: "app-shell__footer-user-panel-actions") do
                    button_to("Log out", Current.session, method: :delete, class: "app-shell__footer-user-panel-button")
                  end
                end
              end
            end

          end
        end
      end
    end
  end

  def flash
    page_info.flash || {}
  end
end
