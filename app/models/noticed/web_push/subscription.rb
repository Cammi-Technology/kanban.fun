module Noticed::WebPush
  class Subscription < ApplicationRecord
    self.table_name = "noticed_web_push_subscriptions"

    belongs_to :user

    validates :endpoint, presence: true, uniqueness: true
    validates :p256dh, presence: true
    validates :auth, presence: true

    def publish(data)
      WebPush.payload_send(
        message: data.to_json,
        endpoint: endpoint,
        p256dh: p256dh,
        auth: auth,
        vapid: {
          private_key: Rails.application.credentials.dig(:web_push, :private_key),
          public_key: Rails.application.credentials.dig(:web_push, :public_key)
        }
      )
    end
  end
end
