class AccountsController < ApplicationController
  def new
    authorize(Account, :new?)

    render Views::Accounts::New.new
  end

  def create
    authorize(Account, :create?)

    ActiveRecord::Base.transaction do
      @account = Current.user.accounts.create!(account_params)
      Current.user.account_users.create!(account: @account)
    end

    redirect_to account_dashboard_path(@account), notice: t(".success")
  rescue ActiveRecord::RecordInvalid => e
    flash.now[:alert] = t(".error")
    render Views::Accounts::New.new(account: e.record)
  end

  def index
    accounts = policy_scope(Account).all

    return redirect_to new_account_path if Current.user.accounts.empty?

    render Views::Accounts::Index.new(
      accounts: accounts
    )
  end

  private

  def account_params
    params.expect(account: [ :name ])
  end
end
