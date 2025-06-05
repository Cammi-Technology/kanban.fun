# frozen_string_literal: true

class Views::Accounts::New < Views::Base
  def view_template
    h1 { t(".title") }
    p { t(".description") }
  end

  private

  def page_title = "Accounts"
end
