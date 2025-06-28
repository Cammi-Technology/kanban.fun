# frozen_string_literal: true

class Components::FormLabel < Components::Base
  prop :for, String

  def view_template(&)
    label(**@attrs, &)
  end

  def default_attrs = { for: @for }
end
