require "test_helper"

class AccountTest < ActiveSupport::TestCase
  setup do
    @account = accounts(:account)
    @account_user = users(:account_user)
  end

  test "includes account user" do
    assert_includes @account.users, @account_user
  end
end
