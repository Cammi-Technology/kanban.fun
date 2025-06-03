class HomeController < ApplicationController
  def index
    authorize(Current.user, :visit_home?)

    render Views::Home::Index.new
  end
end
