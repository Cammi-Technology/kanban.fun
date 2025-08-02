module Projects
  extend ActiveSupport::Concern

  included do
    before_action :set_current_project
  end

  def set_current_project
    raise "params[:project_id] is missing. Please only include in controllers nested inside projects/" unless params[:project_id].present?

    Current.project = authorize(Project.find(params[:project_id]), :set_current_project?)
  end
end
