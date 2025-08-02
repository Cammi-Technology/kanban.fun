class HomeController < ApplicationController
  def index
    authorize(Current.user, :visit_home?)

    return redirect_to accounts_path if Current.user

    render Views::Home::Index.new
  end
end
