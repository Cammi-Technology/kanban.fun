require "test_helper"

class AuthorizationContextTest < ActiveSupport::TestCase
  def setup
    @user = users(:account_user)
    @account_user = account_users(:account_user)
    @authorization_context = AuthorizationContext.new(user: @user)
  end

  test "should have a user" do
    assert_equal(@authorization_context.user, @user)
  end

  test "should have an optional account user" do
    assert_equal(@authorization_context.account_user, nil)

    assert_equal(
      AuthorizationContext.new(user: @user, account_user: @account_user).account_user,
      @account_user
    )
  end
end
