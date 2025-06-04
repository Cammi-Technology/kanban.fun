require "test_helper"

class AccountUserScopingTest < ActionDispatch::IntegrationTest
  setup do
    @account_user = account_users(:account_user)
    @account = accounts(:cammi)
    @user = users(:account_user)
  end

  test "should set Current.account_user from account_id" do
    sign_in_as(@user)
    get account_dashboard_path(@account)

    assert_equal @account_user, Current.account_user
  end
end
