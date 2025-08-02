require "test_helper"

class CurrentTest < ActiveSupport::TestCase
  setup do
    @account_user = account_users(:account_user)
  end

  test "Current.account_user is nil by default" do
    assert_nil Current.account_user
  end

  test "Current.account_user can be set" do
    Current.account_user = @account_user
    assert_equal @account_user, Current.account_user
  end

  test "Current.account can be set" do
    Current.account = @account_user.account
    assert_equal @account_user.account, Current.account
  end

  test "Current.project can be set" do
    Current.project = projects(:project)
    assert_equal projects(:project), Current.project
  end
end
