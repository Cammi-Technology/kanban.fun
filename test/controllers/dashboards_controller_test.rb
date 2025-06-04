require "test_helper"

class DashboardsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @account_user = account_users(:account_user)
    @user = users(:account_user)
    @account = accounts(:cammi)
    @other_account = accounts(:other_account)
  end

  test "should get show" do
    sign_in_as(@user)
    get account_dashboard_path(@account)
    assert_response :success
    assert_equal @account.id, @user.reload.last_viewed_account_id
  end

  test "sould not get show without sign in" do
    get account_dashboard_path(@account)
    assert_requires_authentication
  end

  test "should not get other account's dashboard" do
    sign_in_as(@user)
    get account_dashboard_path(@other_account)
    assert_response :not_found
  end
end
