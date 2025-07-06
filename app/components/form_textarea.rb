# frozen_string_literal: true

class Components::FormTextarea < Components::Base
  prop :id, String, reader: :private
  prop :name, String, reader: :private
  prop :required, _Boolean, default: true, reader: :private
  prop :value, _Nilable(String), default: "", reader: :private

  def view_template
    textarea(**@attrs)
  end

  def default_attrs = {
    id: id, name: name, required: required, value: value
  }
end
