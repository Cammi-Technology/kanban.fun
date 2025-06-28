# frozen_string_literal: true

class Views::Dashboard::Show < Views::Base
  def view_template
    h1 { "Dashboard::Show" }
    p { "Find me in app/views/dashboard/show.rb" }
  end

  def page_title = "Yay"
end
