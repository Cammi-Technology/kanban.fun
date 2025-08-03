class WebPushSubscriptionsController < ApplicationController
  skip_after_action :verify_pundit_authorization

  def create
    subscription = Current.user.web_push_subscriptions.find_or_initialize_by(endpoint: subscription_params[:endpoint])

    if subscription.persisted?
      Rails.logger.info "WebPush subscription already exists for user #{Current.user.id} with endpoint: #{params[:push_subscription][:endpoint]}"
      return render json: {}, status: :found
    end

    subscription.assign_attributes(subscription_params)
    subscription.save!

    Rails.logger.info "WebPush subscription created for user #{Current.user.id} with endpoint: #{params[:push_subscription][:endpoint]}"

    render json: {}, status: :created
  end

  def destroy
    Current.user.web_push_subscriptions.find_by!(endpoint: params[:endpoint]).destroy
    Rails.logger.info "WebPush subscription deleted for user #{Current.user.id} with endpoint: #{params[:push_subscription][:endpoint]}"
    render json: {}
  end

  private

  def subscription_params
    params.expect(push_subscription: [ :endpoint, :p256dh, :auth ])
  end

  def authenticate
    if session_record = Session.find_by_id(cookies.signed[:session_token])
      Current.session = session_record
    else
      head :unauthorized
    end
  end
end
