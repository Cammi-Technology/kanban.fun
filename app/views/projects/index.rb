# frozen_string_literal: true

class Views::Projects::Index < Views::Base
  prop :projects, ActiveRecord::Relation(Project), reader: :private

  def view_template
    h1 { t(".title") }
    p { t(".description") }

    ul do
      projects.each do |project|
        li do
          a(href: account_project_path(project.account, project)) { project.name }
        end
      end
    end
  end

  private

  def page_title = t(".title")
end
