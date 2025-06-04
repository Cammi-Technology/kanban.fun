# frozen_string_literal: true

class Views::Accounts::Index < Views::Base
  prop :accounts, ActiveRecord::Relation(Account), reader: :private

  def view_template
    h1 { t(".title") }
    p { t(".description") }

    ul do
      accounts.each do |account|
        li do
          a(href: account_dashboard_path(account)) { account.name }
        end
      end
    end
  end

  private

  def page_title = "Accounts"
end
