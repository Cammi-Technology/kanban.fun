require "test_helper"

class AccountUserPolicyTest < ActiveSupport::TestCase
  def setup
    @account = accounts(:account)
    @project = projects(:project)
    @account_owner = account_users(:account_owner)
    @account_user = account_users(:account_user)
    @other_account_user = account_users(:other_account_owner)
    @other_project = projects(:other_accounts_project)
  end

  def test_scope
    assert_includes(
      AccountUserPolicy::Scope.new(@account_owner, AccountUser).resolve,
      @account_user,
      "should include account user in same account"
    )
    assert_includes(
      AccountUserPolicy::Scope.new(@account_owner, AccountUser).resolve,
      @account_owner,
      "should include account user in same account"
    )
    refute_includes(
      AccountUserPolicy::Scope.new(@account_owner, AccountUser).resolve,
      @other_account_user,
      "should not include account user in different account"
    )
  end
end
