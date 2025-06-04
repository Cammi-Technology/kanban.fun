require "test_helper"
class AccountsControllerTest < ActionDispatch::IntegrationTest

  setup do
    @account = accounts(:account)
    @other_users_account = accounts(:totally_games)
    @account_owner = users(:account_owner)
    @user = @account_owner
    @account_user = users(:account_user)
  end

  test "should get index when signed in" do
    sign_in_as(@user)
    get accounts_url
    assert_response :success
  end

  test "index should be unauthorized when not signed in" do
    get accounts_url
    assert_requires_authentication
  end

  test "should not get other users' accounts" do
    get accounts_url
    refute_includes response.body, @other_users_account.name
  end
end
