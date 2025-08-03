require "test_helper"

class NewPostNotifierTest < ActiveSupport::TestCase
  include ActionMailer::TestHelper

  setup do
    DeliveryMethods::WebPush.any_instance.stubs(:deliver)
  end

  test "should notify users by email" do
    assert_emails 1 do
      perform_enqueued_jobs do
        NewPostNotifier.with(record: posts(:post)).deliver(users(:account_owner))
      end
    end
  end

  test "should notify users by web push" do
    perform_enqueued_jobs do
      DeliveryMethods::WebPush.any_instance.expects(:deliver)

      NewPostNotifier.with(record: posts(:post)).deliver(users(:account_owner))
    end
  end

  test "should not notify the author by web push" do
    perform_enqueued_jobs do
      DeliveryMethods::WebPush.any_instance.expects(:deliver).never

      NewPostNotifier.with(record: posts(:post)).deliver(users(:account_user))
    end
  end

  test "should not notify the author by email" do
    assert_no_emails do
      perform_enqueued_jobs do
        NewPostNotifier.with(record: posts(:post)).deliver(users(:account_user))
      end
    end
  end
end
