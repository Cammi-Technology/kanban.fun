class DashboardsController < ApplicationController
  def show
    account = Current.account_user.account

    authorize account, :visit_dashboard?

    render plain: "Dashboard for account #{account.id}"
  end
end
