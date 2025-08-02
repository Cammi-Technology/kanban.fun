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

  def not_author?(notification)
    notification.record.author.user != notification.recipient
  end
  #
  # bulk_deliver_by :slack do |config|
  #   config.url = -> { Rails.application.credentials.slack_webhook_url }
  # end
  #
  # deliver_by :custom do |config|
  #   config.class = "MyDeliveryMethod"
  # end

  # Add required params
  #
  # required_param :message

  # Compute recipients without having to pass them in
  #
  # recipients do
  #   params[:record].thread.all_authors
  # end
end
