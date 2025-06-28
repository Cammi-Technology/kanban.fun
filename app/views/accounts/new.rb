# frozen_string_literal: true

class Views::Accounts::New < Views::Base
  prop :account, Account, reader: :private, default: -> { Account.new }

  def view_template
    h1 { t(".title") }
    p { t(".description") }
  end

  private

  def page_title = "Accounts"
end
