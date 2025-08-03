class AccountUsersController < ApplicationController
  def index
    account_users = policy_scope(AccountUser)
      .joins(:user)
      .where(account: Current.account)
      .where("users.first_name || ' ' || users.last_name LIKE :query", query: "%#{params[:query]}%")

    render json: account_users, only: [ :id ], methods: [ :name, :attachable_sgid ]
  end

  private

  def authenticate
    if session_record = Session.find_by_id(cookies.signed[:session_token])
      Current.session = session_record
    else
      head :unauthorized
    end
  end
end
