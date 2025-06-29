require "test_helper"

class UserTest < ActiveSupport::TestCase
  setup do
    @user = users(:account_owner).dup
  end

  test "should have no accounts" do
    assert_equal 0, @user.accounts.count
  end

  test "should have account users" do
    assert_includes users(:account_owner).account_users, account_users(:account_owner)
  end

  test "should require first name" do
    @user.first_name = ""
    refute @user.valid?
  end

  test "should require last name" do
    @user.last_name = ""
    refute @user.valid?
  end
end
