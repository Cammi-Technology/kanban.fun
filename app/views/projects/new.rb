# frozen_string_literal: true

class Views::Projects::New < Views::Base
  include Phlex::Rails::Helpers::FormWith

  prop :project, Project, reader: :private

  def view_template
    ContentShell(width: :narrow, class: "project-new") do
      show_form
    end
  end

  private

  def page_title = t(".title")

  def show_form
    form_with model: [ project.account, project ], class: "project-new__form" do |form|
      div(class: "project-new__panel surface-panel") do
        h1(class: "sr-only") do
          t(".title")
        end

        if form.object.errors.any?
          ul(class: "field-errors project-new__errors") do
            form.object.errors.full_messages.each do |message|
              li(class: "field-error project-new__error") { message }
            end
          end
        end

        div(class: "project-new__fields") do
          div(class: "project-new__field") do
            FormField do
              FormLabel(
                for: "project_name",
                class: "project-new__label"
              ) { t("activerecord.attributes.project.name") }
              FormInput(
                name: "project[name]",
                id: "project_name",
                required: true,
                placeholder: t("placeholders.project.name"),
                value: form.object.name,
                class: "project-new__input"
              )
            end
          end

          div(class: "project-new__field") do
            FormField do
              FormLabel(
                for: "project_description",
                class: "project-new__label"
              ) do
                t("activerecord.attributes.project.description")
              end
              FormTextarea(
                name: "project[description]",
                id: "project_description",
                required: false,
                placeholder: t("placeholders.project.description"),
                value: form.object.description,
                rows: 12,
                class: "project-new__textarea"
              )
            end
          end
        end

        footer(class: "project-new__footer") do
          Button(type: "submit", class: "project-new__submit primary-button") do
            "Create Project"
          end
        end
      end
    end
  end
end
