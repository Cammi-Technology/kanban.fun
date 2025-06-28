class DashboardsController < ApplicationController
  def show
    account = Current.account_user.account

    authorize account, :visit_dashboard?

    render Views::Dashboard::Show.new
  end
end
