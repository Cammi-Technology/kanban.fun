require "test_helper"

class AccountTest < ActiveSupport::TestCase
  setup do
    @account = accounts(:account)
    @other_users_account = accounts(:totally_games)
    @account_user = users(:account_user)
  end

  test "includes account user" do
    assert_includes @account.users, @account_user
  end

  test "should require name" do
    @account.name = ""
    refute @account.valid?
  end

  test "should require unique name" do
    @account.name = @other_users_account.name
    refute @account.valid?
  end

  test "should have projects" do
    assert_includes @account.projects, projects(:project)
  end
end
