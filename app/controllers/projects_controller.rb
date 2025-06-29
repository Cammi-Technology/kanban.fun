class ProjectsController < ApplicationController
  def index
    authorize(Project, :index?)

    if Current.account.projects.empty?
      return redirect_to new_account_project_path(Current.account)
    end

    render Views::Projects::Index.new(
      projects: Current.account.projects
    )
  end

  def new
    project = Current.account.projects.new

    authorize(project, :new?)

    render Views::Projects::New.new(
      project: project
    )
  end

  def show
    render Views::Projects::Show.new(
      project: authorize(Current.account.projects.find(params[:id]), :show?)
    )
  end


  def create
    authorize(
      project = Current.account.projects.new(project_params),
      :create?
    )

    project.save!

    redirect_to [ project.account, project ], notice: t("projects.create.success")
  rescue ActiveRecord::RecordInvalid => e
    render Views::Projects::New.new(
      project: e.record
    ), status: :unprocessable_entity
  end

  private

  def project_params
    params.expect(project: [ :name, :description ])
  end
end
