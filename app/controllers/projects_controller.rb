class ProjectsController < ApplicationController
  def index
    authorize(Project, :index?)

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
    project = Current.account.projects.create!(project_params)

    authorize(project, :create?)

    redirect_to [ project.account, project ], notice: t("projects.create.success")
  rescue ActiveRecord::RecordInvalid => e
    render Views::Projects::New.new(
      project: e.record
    )
  end

  private

  def project_params
    params.expect(project: [ :name, :description ])
  end
end
