# frozen_string_literal: true

class Components::Button < Components::Base
  def view_template(&)
    button(**@attrs) do
      return yield if block_given?

      t(".button_text")
    end
  end
end
