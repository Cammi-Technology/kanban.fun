# frozen_string_literal: true

class Components::QuickActionTile < Components::Base
  prop :href, _String
  prop :icon, Symbol, &:to_sym
  prop :label, String

  def view_template
    a(**@attrs) do
      span(class: "quick-action-tile__icon", aria: { hidden: "true" }) do
        Icon(icon_name)
      end
      span(class: "quick-action-tile__label") { @label }
    end
  end

  private

  def default_attrs = {
    href: @href,
    title: @label,
    class: "quick-action-tile"
  }

  def icon_name = "bootstrap/#{@icon.to_s.tr('_', '-')}"
end
