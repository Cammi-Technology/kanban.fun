# frozen_string_literal: true

class Views::Base < Components::Base
  def around_template
    render Components::ApplicationLayout.new(page_info) do
      super
    end
  end

  def page_info
    PageInfo.new(title: page_title, flash: view_context.flash)
  end
end
