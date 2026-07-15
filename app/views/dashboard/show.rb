# frozen_string_literal: true

class Views::Dashboard::Show < Views::Base
  include PhlexIcons

  prop :projects, ActiveRecord::Relation(Project)

  def view_template
    div(class: "dashboard-projects") do
      h1(class: "dashboard-projects__title") do
        Current.account.name
      end

      div(class: "dashboard-projects__actions") do
        a(
          href: new_account_project_path(Current.account),
          class: "dashboard-projects__new-project"
        ) do
          span(
            class: "dashboard-projects__new-project-icon",
            aria: { hidden: "true" }
          ) do
            Icon("bootstrap/plus")
          end
          span { "Make a new project" }
        end
      end

      ul(class: "dashboard-projects__list") do
        @projects.each do |project|
          li(class: "dashboard-projects__item") do
            a(
              href: account_project_path(Current.account, project),
              class: "dashboard-projects__link"
            ) do
              project.name
            end
          end
        end
      end
    end
  end

  def page_title = Current.account.name
end
