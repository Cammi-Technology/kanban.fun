require "test_helper"

class Noticed::WebPush::SubscriptionTest < ActiveSupport::TestCase
  test "validates presence" do
    subscription = Noticed::WebPush::Subscription.new
    assert_not subscription.valid?
    assert_not_empty subscription.errors[:endpoint]
    assert_not_empty subscription.errors[:p256dh]
    assert_not_empty subscription.errors[:auth]
  end

  test "validates uniqueness of endpoint" do
    existing = noticed_web_push_subscriptions(:one)
    duplicate = existing.dup
    assert_not duplicate.valid?
    assert_not_empty duplicate.errors[:endpoint]
  end
end
