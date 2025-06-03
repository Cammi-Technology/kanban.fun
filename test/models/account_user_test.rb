require "test_helper"

class AccountUserTest < ActiveSupport::TestCase
  setup do
    @account_user = account_users(:account_user)
    @user = users(:account_user)
    @account = accounts(:cammi)
  end

  test "should include account user" do
    assert_equal @account_user.user, @user
  end

  test "should belong to account" do
    assert_equal @account, @account_user.account
  end
end
