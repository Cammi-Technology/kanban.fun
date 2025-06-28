# frozen_string_literal: true

class Components::Base < Phlex::HTML
  extend Literal::Properties

  include Phlex::Rails::Helpers::T
  include Phlex::Rails::Helpers::Routes

  prop :attrs, Hash, :**, reader: :private do |value|
    merge_attrs(value, default_attrs)
  end

  def merge_attrs(user_attrs, default_attrs)
    mix(default_attrs, user_attrs)
  end

  def default_attrs = {}

  if Rails.env.development?
    def before_template
      comment { "Before #{self.class.name}" }
      super
      comment { "After #{self.class.name}" }
    end
  end
end
