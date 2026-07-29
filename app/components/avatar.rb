# frozen_string_literal: true

class Components::Avatar < Components::Base
  SIZES = {
    sm: "avatar--sm",
    md: "avatar--md",
    lg: "avatar--lg"
  }.freeze

  Size = _Union(*SIZES.keys)

  prop :name, String, reader: :private
  prop :size, Size, default: :md, reader: :private, &:to_sym

  def view_template
    div(**@attrs, aria: { hidden: "true" }) do
      initials
    end
  end

  private

  def default_attrs = { class: avatar_classes }

  def avatar_classes
    [ "avatar", SIZES.fetch(size) ]
  end

  def initials
    name.split.map(&:first).first(2).join.upcase
  end
end
