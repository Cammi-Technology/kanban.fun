# frozen_string_literal: true

class Components::ProjectDropdown < Components::Base
  include PhlexIcons

  prop :projects, ActiveRecord::Relation(Project)

  register_value_helper :params

  def view_template
    return unless Current.user

    div(
      class: "project-dropdown",
      data_controller: "project-navigation-dropdown"
    ) do
      button(
        type: "button",
        class: "project-dropdown__trigger",
        aria: { haspopup: "dialog", expanded: "false" },
        data_action: "project-navigation-dropdown#open",
        data_project_navigation_dropdown_target: "trigger"
      ) do
        span(
          class: "project-dropdown__trigger-label"
        ) { current_project&.name || t("components.project_dropdown.trigger") }
        span(
          class: "project-dropdown__trigger-icon",
          aria: { hidden: "true" }
        ) do
          Icon("bootstrap/chevron-down")
        end
      end

      dialog(
        class: "project-dropdown__dialog",
        aria: { labelledby: "project-dropdown-title" },
        data_action: <<~ACTIONS.squish,
          click->project-navigation-dropdown#backdropClose
          cancel->project-navigation-dropdown#cancel
          close->project-navigation-dropdown#closed
        ACTIONS
        data_project_navigation_dropdown_target: "dialog"
      ) do
        div(class: "project-dropdown__content") do
          if current_project
            nav(
              aria: { label: t("components.project_dropdown.shortcuts_label") },
              class: "project-dropdown__quick-actions"
            ) do
              a(
                href: account_project_posts_path(Current.account, current_project),
                class: "project-dropdown__quick-action"
              ) do
                span(
                  class: "project-dropdown__quick-action-icon",
                  aria: { hidden: "true" }
                ) do
                  Icon("bootstrap/file-post")
                end
                span(
                  class: "project-dropdown__quick-action-label"
                ) { t("components.project_dropdown.posts") }
              end
            end
          end

          div(class: "project-dropdown__header") do
            h2(
              id: "project-dropdown-title",
              class: "project-dropdown__title"
            ) { t("components.project_dropdown.title") }

            button(
              type: "button",
              class: "project-dropdown__close",
              aria: { label: t("components.project_dropdown.close_label") },
              data_action: "project-navigation-dropdown#close"
            ) do
              plain t("components.project_dropdown.close")
            end
          end

          nav(
            aria: { label: t("components.project_dropdown.projects_label") },
            class: "project-dropdown__nav"
          ) do
            ul(class: "project-dropdown__list") do
              @projects.each do |project|
                project_row(project)
              end
            end
          end
        end
      end
    end
  end

  private

  def project_row(project)
    li(class: "project-dropdown__item") do
      a(
        href: account_project_path(Current.account, project),
        class: "project-dropdown__link",
        aria: current_project?(project) ? { current: "page" } : {}
      ) do
        span(
          class: "project-dropdown__link-icon",
          aria: { hidden: "true" }
        ) do
          Icon("bootstrap/folder")
        end

        span(class: "project-dropdown__link-body") do
          span(
            class: "project-dropdown__link-title"
          ) { project.name }
          span(class: "project-dropdown__link-meta") do
            if current_project?(project)
              t("components.project_dropdown.current_project")
            else
              t("components.project_dropdown.open_project")
            end
          end
        end
      end
    end
  end

  def current_project?(project) = current_project&.id == project.id

  def current_project
    Current.project || current_project_from_params
  end

  def current_project_from_params
    return unless params[:controller] == "projects"
    return unless params[:id].present?

    @current_project_from_params ||= @projects.find_by(id: params[:id])
  end
end
