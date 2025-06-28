require "test_helper"

class UserTest < ActiveSupport::TestCase
  setup do
    @user = User.new
  end

  test "should have no accounts" do
    assert_equal @user.accounts.count, 0
  end
end
