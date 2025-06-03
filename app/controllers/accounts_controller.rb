class AccountsController < ApplicationController
  def index
    render Views::Accounts::Index.new(
      accounts: policy_scope(Account)
    )
  end

  def show
    render Views::Accounts::Show.new(
      account: authorize(Account.find(params[:id]))
    )
  end
end
