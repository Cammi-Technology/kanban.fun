# frozen_string_literal: true

class Views::Projects::New < Views::Base
  include Phlex::Rails::Helpers::FormWith

  prop :project, Project, reader: :private

  def view_template
    p { t(".description") }
    show_form
  end

  private

  def page_title = t(".title")

  def show_form
    form_with model: [ project.account, project ] do |form|
      if form.object.errors.any?
        form.object.errors.full_messages.each do |message|
          plain message
        end
      end

      FormField do
        FormLabel(for: "project_name") { t("activerecord.attributes.project.name") }
        FormInput(
          name: "project[name]",
          id: "project_name",
          required: true,
          placeholder: t("placeholders.project.name"),
          value: form.object.name
        )
      end

      FormField do
        FormLabel(for: "project_description") { t("activerecord.attributes.project.description") }
        FormTextarea(
          name: "project[description]",
          id: "project_description",
          required: false,
          placeholder: t("placeholders.project.description"),
          value: form.object.description
        )
      end

      FormField do
        Button(type: "submit") { "Create Project" }
      end
    end
  end
end
