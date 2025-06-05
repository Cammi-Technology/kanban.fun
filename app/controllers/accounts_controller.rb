class AccountsController < ApplicationController
  def new
    authorize(Current.user, :new_account?)

    render Views::Accounts::New.new
  end

  def index
    accounts = policy_scope(Account).all

    return redirect_to new_account_path if Current.user.accounts.empty?

    render Views::Accounts::Index.new(
      accounts: accounts
    )
  end
end
