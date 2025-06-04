require "test_helper"
require "test_helpers/authentication_helper"

class AccountsControllerTest < ActionDispatch::IntegrationTest
  include AuthenticationHelper

  setup do
    @account = accounts(:cammi)
    @other_users_account = accounts(:totally_games)
    @account_owner = users(:account_owner)
    @user = @account_owner
    @account_user = users(:account_user)
  end

  test "should redirect to account when signed in" do
    sign_in_as(@user)
    get accounts_url
    assert_redirected_to account_dashboard_url(@account)
  end

  test "index should be unauthorized when not signed in" do
    get accounts_url
    assert_requires_authentication
  end
end
