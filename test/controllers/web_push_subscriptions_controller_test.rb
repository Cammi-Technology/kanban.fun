require "test_helper"

class WebPushSubscriptionsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = users(:account_user)
  end

  test "requires authentication" do
    post web_push_subscriptions_path, params: { push_subscription: { endpoint: "url", p256dh: "key", auth: "token" } }
    assert_response :unauthorized

    delete web_push_subscription_path(endpoint: "url")
    assert_response :unauthorized
  end

  test "creates a subscription" do
    sign_in_as @user
    assert_difference "Noticed::WebPush::Subscription.count" do
      post web_push_subscriptions_path(endpoint: "url"), params: { push_subscription: { endpoint: "url", p256dh: "key", auth: "token" } }
      assert_response :success
    end
  end

  test "deletes a subscription" do
    sign_in_as @user

    @user.web_push_subscriptions.create!(endpoint: "url", p256dh: "key", auth: "token")

    assert_difference "Noticed::WebPush::Subscription.count", -1 do
      delete web_push_subscription_path(endpoint: "url"),
        params: { push_subscription: { endpoint: "url" } }
      assert_response :success
    end
  end

  test "404 deleting a missing subscription" do
    sign_in_as @user
    assert_no_difference "Noticed::WebPush::Subscription.count" do
      delete web_push_subscription_path(endpoint: "missing")
      assert_response :missing
    end
  end
end
