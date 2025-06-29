require "test_helper"
class AccountPolicyTest < ActiveSupport::TestCase
  def setup
    @account = accounts(:account)
    @other_account = accounts(:totally_games)
    @user = AuthorizationContext.new(user: users(:account_owner))
  end

  def test_scope
    refute_includes(
      AccountPolicy::Scope.new(@user, Account).resolve,
      @other_account
    )
  end

  def test_visit_dashboard
    assert_permit(@user, @account, :visit_dashboard)
    refute_permit(@user, @other_account, :visit_dashboard)
  end

  test "should permit users to new account" do
    assert_permit(@user, Account, :new)
  end

  test "should permit users to create account" do
    assert_permit(@user, Account, :create)
  end
end
