# frozen_string_literal: true

class Components::FormField < Components::Base
  def view_template
    yield
  end
end
