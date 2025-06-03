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
    assert_no_match @other_users_account.name, response.body
  end

  test "should show when signed in" do
    sign_in_as(@user)
    get account_url(@account)
    assert_response :success
  end

  test "show should be unauthorized when not signed in" do
    get account_url(@account)
    assert_requires_authentication
  end

  test "show should be unauthorized when account does not belong to user" do
    sign_in_as(@user)

    assert_raises(Pundit::NotAuthorizedError) do
      get account_url(@other_users_account)
    end
  end

  test "show should show account owner" do
    sign_in_as(@user)
    get account_url(@account)
    assert_includes response.body, @account_owner.name
  end

  test "should show account users" do
    sign_in_as(@user)
    get account_url(@account)
    assert_includes response.body, @account_user.name
  end
end
