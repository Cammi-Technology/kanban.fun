require "test_helper"

class UserTest < ActiveSupport::TestCase
  setup do
    @user = User.new
  end

  test "should have no accounts" do
    assert_equal @user.accounts.count, 0
  end

  test "should have account users" do
    assert_includes users(:account_owner).account_users, account_users(:account_owner)
  end
end
