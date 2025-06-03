require "test_helper"

class AccountTest < ActiveSupport::TestCase
  setup do
    @account = accounts(:cammi)
    @account_user = users(:account_user)
  end

  test "includes account user" do
    assert_includes @account.users, @account_user
  end
end
