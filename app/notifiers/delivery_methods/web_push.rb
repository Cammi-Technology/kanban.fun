class DeliveryMethods::WebPush < ApplicationDeliveryMethod
  required_options :data_method

  def deliver
    recipient.web_push_subscriptions.each do |subscription|
      subscription.publish(data)
    rescue ::WebPush::ExpiredSubscription
      Rails.logger.info "Removing expired WebPush subscription"
      subscription.destroy
    rescue ::WebPush::Unauthorized
      Rails.logger.info "Removing unauthorized WebPush subscription"
      subscription.destroy
    end
  end

  private

  def data
    notification.send(config.fetch(:data_method, :web_push_data))
  end
end
