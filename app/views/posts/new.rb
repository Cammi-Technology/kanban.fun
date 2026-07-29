# frozen_string_literal: true

class Views::Posts::New < Views::Base
  include Phlex::Rails::Helpers::FormWith

  prop :post, Post, reader: :private

  def view_template
    ContentShell(width: :wide, class: "post-editor") do
      p(class: "post-editor__breadcrumb") do
        plain Current.project.name
        plain "  <  "
        plain t("views.posts.index.title")
      end

      show_form
    end
  end

  private

  def page_title = t(title_key)

  def title_key
    post.persisted? ? "views.posts.edit.title" : ".title"
  end

  def show_form
    form_with model: [ post.project.account, post.project, post ], class: "post-editor__form" do |form|
      div(class: "post-editor__panel surface-panel") do
        h1(class: "sr-only") { t(title_key) }

        if form.object.errors.any?
          ul(class: "field-errors post-editor__errors") do
            form.object.errors.full_messages.each do |message|
              li(class: "field-error post-editor__error") { message }
            end
          end
        end

        div(class: "post-editor__fields") do
          div(class: "post-editor__field") do
            FormField do
              FormLabel(
                for: "post_title",
                class: "sr-only"
              ) { t("activerecord.attributes.post.title") }
              FormInput(
                name: "post[title]",
                id: "post_title",
                required: true,
                placeholder: t("placeholders.post.title"),
                value: form.object.title,
                class: "post-editor__input"
              )
            end
          end

          div(class: "post-editor__field") do
            FormField do
              FormLabel(
                for: "post_content",
                class: "sr-only"
              ) { t("activerecord.attributes.post.content") }
              form.rich_text_area(
                :content,
                class: "post-editor__content",
                data: {
                  controller: "mentions",
                  mentions_target: "input",
                  mentions_url_value: account_project_account_users_path(
                    Current.account,
                    Current.project,
                    format: :json
                  )
                }
              )
            end
          end
        end

        footer(class: "post-editor__footer") do
          Button(
            name: "post[published]",
            value: "true",
            type: "submit",
            class: "post-editor__submit primary-button"
          ) do
            submit_label
          end
        end
      end
    end
  end

  def submit_label
    post.persisted? ? "Update this message" : "Post this message"
  end
end
