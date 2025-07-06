# frozen_string_literal: true

class Components::FormRichTextarea < Components::Base
  register_element :trix_editor

  prop :id, String, reader: :private
  prop :name, String, reader: :private
  prop :required, _Boolean, default: true, reader: :private
  prop :value, _Nilable(ActionText::RichText), default: "", reader: :private

  def view_template
    input(type: "hidden", id: id, name: name, value: value&.body&.to_trix_html)
    trix_editor(**@attrs)
  end

  def default_attrs = {
    id: id,
    name: name,
    required: required,
    value: value&.body&.to_trix_html,
    class: "trix-content"
  }
end
