require "test_helper"
require "test_helpers/authorization_helper"

class AccountPolicyTest < ActiveSupport::TestCase
  include AuthorizationHelper

  def setup
    @account = accounts(:cammi)
    @other_account = accounts(:totally_games)
    @user = users(:account_owner)
  end

  def test_scope
    refute_includes(
      AccountPolicy::Scope.new(@user, Account).resolve,
      @other_account
    )
  end

  def test_show
    assert_permit(@user, @account, :show)
    refute_permit(@user, @other_account, :show)
  end
end
