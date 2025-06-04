class AccountsController < ApplicationController
  def index
    render Views::Accounts::Index.new(
      accounts: policy_scope(Account)
    )
  end
end
