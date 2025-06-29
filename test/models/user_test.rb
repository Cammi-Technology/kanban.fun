require "test_helper"

class UserTest < ActiveSupport::TestCase
  setup do
    @user = User.new
  end

  test "should have no accounts by default" do
    assert_equal 0, @user.accounts.count
  end

  test "should have account users" do
    assert_includes users(:account_owner).account_users, account_users(:account_owner)
  end
end
