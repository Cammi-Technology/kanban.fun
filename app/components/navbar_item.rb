# frozen_string_literal: true

class Components::NavbarItem < Components::Base
  include PhlexIcons

  prop :icon, String, reader: :private
  prop :label, String, reader: :private
  prop :href, String, reader: :private

  def view_template
    a(href: href, class: "navbar__item") do
      span(class: "navbar__icon") do
        Icon("bootstrap/#{icon}")
      end
    end
  end
end
