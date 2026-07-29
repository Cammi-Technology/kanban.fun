# frozen_string_literal: true

class Views::Projects::Show < Views::Base
  prop :project, Project, reader: :private

  def view_template
    ContentShell(width: :narrow, class: "project-show") do
      div(class: "project-show__header") do
        h1(class: "project-show__title") { project.name }
        p(class: "project-show__description") { project.description } if project.description.present?
      end

      nav(
        aria: { label: t(".title") },
        class: "project-dropdown__quick-actions project-show__tiles"
      ) do
        QuickActionTile(
          href: account_project_posts_path(project.account, project),
          icon: :file_post,
          label: t(".posts")
        )
      end
    end
  end

  private

  def page_title = t(".title")
end
