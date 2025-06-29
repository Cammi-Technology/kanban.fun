# frozen_string_literal: true

class Components::FormInput < Components::Base
  prop :id, String, reader: :private
  prop :name, String, reader: :private
  prop :required, _Boolean, default: true, reader: :private

  def view_template
    input(**@attrs)
  end

  def default_attrs = {
    id: id, name: name, required: required
  }
end
