# frozen_string_literal: true

class Components::CommentForm < Components::Base
  include Phlex::Rails::Helpers::FormWith

  prop :record, _Any, reader: :private
  prop :comment, _Nilable(Comment), default: nil, reader: :private

  def view_template
    form_with(
      model: [ Current.account, Current.project, comment_instance.record, comment_instance ],
      **@attrs
    ) do |form|
      if form.object.errors.any?
        form.object.errors.full_messages.each do |message|
          plain message
        end
      end

      FormField do
        form.rich_text_area :content, data: {
          controller: "mentions",
          mentions_target: "input",
          mentions_url_value: account_project_account_users_path(Current.account, Current.project, format: :json)
        }
      end

      FormField do
        Button(type: "submit", class: "primary-button") do
          comment.present? ? "Update Comment" : "Add Comment"
        end
      end
    end
  end

  private

  def comment_instance
    @comment_instance ||= comment || Comment.new(record: record)
  end
end
