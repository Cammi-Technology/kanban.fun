require "test_helper"

class NewPostNotifierTest < ActiveSupport::TestCase
  include ActionMailer::TestHelper

  test "should notify users by email" do
    assert_emails 1 do
      perform_enqueued_jobs do
        NewPostNotifier.with(record: posts(:post)).deliver(users(:account_owner))
      end
    end
  end

  test "should not notify the author" do
    assert_no_emails do
      perform_enqueued_jobs do
        NewPostNotifier.with(record: posts(:post)).deliver(users(:account_user))
      end
    end
  end
end
