require "test_helper"
class AccountsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @account = accounts(:account)
    @other_users_account = accounts(:totally_games)
    @account_owner = users(:account_owner)
    @user = @account_owner
    @account_user = users(:account_user)
    @user_without_account = users(:user_without_account)
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

  test "should redirect to new_account_path when there are no accounts" do
    sign_in_as(@user_without_account)
    get accounts_url
    assert_redirected_to new_account_path
  end

  test "should get new when signed in" do
    get new_account_url
    assert_requires_authentication

    sign_in_as(@user)
    get new_account_url
    assert_response :success
  end

  test "should create account when signed in" do
    post accounts_url
    assert_requires_authentication

    sign_in_as(@user)
    assert_difference -> { @user.reload.accounts.count } do
      post accounts_url, params: { account: { name: "New Account" } }
    end

    assert_redirected_to account_dashboard_url(
      @user.accounts.order(id: :desc).limit(1).last
    )
  end

  test "should create an account user when creating an account" do
    sign_in_as(@user)

    assert_difference -> { @user.account_users.count } do
      post accounts_url, params: { account: { name: "New Account" } }
    end

    assert_equal @user.account_users.last.account, @user.accounts.order(id: :desc).limit(1).last
  end

  test "should not create account with invalid params" do
    sign_in_as(@user)
    assert_no_difference -> { @user.reload.accounts.count } do
      post accounts_url, params: { account: { name: "" } }
    end

    assert_response :success
  end
end
