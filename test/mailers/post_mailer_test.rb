require "test_helper"

class PostMailerTest < ActionMailer::TestCase
  setup do
    @user = users(:lazaro_nixon)
  end

  test "new_post" do
    mail = PostMailer.with(recipient: @user).new_post
    assert_equal [ @user.email ], mail.to
  end
end
