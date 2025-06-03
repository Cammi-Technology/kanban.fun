# frozen_string_literal: true

class Views::Accounts::Show < Views::Base
  prop :account, Account, reader: :private

  def view_template
    h1 { account.name }
    p do
      plain "created: "
      time(datetime: account.created_at) { plain account.created_at.to_fs(:long) }
    end

    p do
      strong { "Owner: " }
      plain "#{account.owner.name}"
    end

    p do
      strong { "Users: " }
      ul do
        account_users.each do |user|
          li { plain user.name }
        end
      end
    end
  end

  private

  def page_title = "Account"

  def account_users
    account.users - [ account.owner ]
  end
end
