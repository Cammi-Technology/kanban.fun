# frozen_string_literal: true

class Views::Dashboard::Show < Views::Base
  prop :projects, ActiveRecord::Relation(Project)

  def view_template
    h1 { "Dashboard::Show" }

    ul do
      @projects.each do |project|
        li do
          a(href: account_project_path(Current.account, project)) do
            project.name
          end
        end
      end
    end
  end

  def page_title = "Yay"
end
