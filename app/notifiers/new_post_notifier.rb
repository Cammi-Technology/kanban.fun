# To deliver this notification:
#
# NewPostNotifier.with(record: @post, message: "New post").deliver(User.all)

class NewPostNotifier < ApplicationNotifier
  # Add your delivery methods
  #
  deliver_by :email do |config|
    config.mailer = "PostMailer"
    config.method = "new_post"
    config.params ->(recipient) {
      {
        user: recipient
      }
    }
    config.if = :not_author?
  end

  deliver_by :web_push, data_method: :web_push_message, class: "DeliveryMethods::WebPush", if: :not_author?

  def not_author?(notification)
    notification.record.author.user != notification.recipient
  end

  notification_methods do
    include ActionView::Helpers::TextHelper

    def title
      truncate("#{record.author.user.name.familiar} posted #{record.title}", length: 50)
    end

    def message
      @message ||= truncate(record.content.to_plain_text, length: 100)
    end

    def web_push_message
      {
        title: title,
        body: message,
        path: account_project_post_path(record.account, record.project, record)
      }
    end
  end
end
