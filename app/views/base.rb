# frozen_string_literal: true

class Views::Base < Components::Base
  include Phlex::Rails::Helpers::T
  include Phlex::Rails::Helpers::Routes

  def around_template
    render Components::ApplicationLayout.new(page_info) do
      super
    end
  end

  def page_info
    PageInfo.new(title: page_title)
  end
end
