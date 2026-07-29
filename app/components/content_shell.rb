# frozen_string_literal: true

class Components::ContentShell < Components::Base
  WIDTHS = %i[wide narrow].freeze

  Width = _Union(*WIDTHS)

  prop :width, Width, default: :wide, &:to_sym

  def view_template(&)
    div(**@attrs, &)
  end

  private

  def default_attrs = { class: shell_classes }

  def shell_classes
    [ "content-shell", "content-shell--#{@width}" ]
  end
end
