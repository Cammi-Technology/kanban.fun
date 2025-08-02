class DashboardsController < ApplicationController
  def show
    account = Current.account_user.account

    authorize account, :visit_dashboard?

    projects = policy_scope(Project).where(account: account)

    render Views::Dashboard::Show.new(
      projects: projects
    )
  end
end
