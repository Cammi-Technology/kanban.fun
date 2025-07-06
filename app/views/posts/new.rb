# frozen_string_literal: true

class Views::Posts::New < Views::Base
  include Phlex::Rails::Helpers::FormWith

  prop :post, Post, reader: :private

  def view_template
    p { t(".description") }
    show_form
  end

  private

  def page_title = t(".title")

  def show_form
    form_with model: [ post.project.account, post.project, post ] do |form|
      if form.object.errors.any?
        form.object.errors.full_messages.each do |message|
          plain message
        end
      end

      FormField do
        FormLabel(for: "post_title") { t("activerecord.attributes.post.title") }
        FormInput(
          name: "post[title]",
          id: "post_title",
          required: true,
          placeholder: t("placeholders.post.title"),
          value: form.object.title
        )
      end

      FormField do
        FormLabel(for: "post_content") { t("activerecord.attributes.project.description") }
        FormRichTextarea(
          name: "post[content]",
          id: "post_content",
          required: false,
          placeholder: t("placeholders.post.content"),
          value: form.object.content
        )
      end

      FormField do
        Button(name: "post[published]", value: "true", type: "submit") { "Post this message" }
      end
    end
  end
end
