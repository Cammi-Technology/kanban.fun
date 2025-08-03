# frozen_string_literal: true

class Components::ApplicationLayout < Components::Base
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
        # Enable PWA manifest for installable apps (make sure to enable in config/routes.rb too!)
        # = tag.link rel: "manifest", href: pwa_manifest_path(format: :json)
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
        nav do
          NavbarItem(
            href: root_path, icon: "house-door-fill", label: "Home"
          )
        end
        header do
          NavbarItem(
            href: account_projects_path(Current.account), icon: "stack", label: "Projects"
          ) if Current.account
          NavbarItem(
            href: accounts_path, icon: "gear-fill", label: "Account"
          )
        end
        main do
          yield
        end
        footer do
          plain "footer"
        end
      end
    end
  end

  def flash
    page_info.flash || {}
  end
end
