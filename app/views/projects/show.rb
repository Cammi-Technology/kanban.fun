# frozen_string_literal: true

class Views::Projects::Show < Views::Base
  prop :project, Project, reader: :private

  def view_template
    h1 { project.name }
    p { project.description } if project.description.present?
    a(href: account_project_posts_path(project.account, project)) do
      t(".posts")
    end
  end

  private

  def page_title = t(".title")
end
