require "test_helper"
require "test_helpers/component_test_helper"

class ViewsAccountsNewTest < ActiveSupport::TestCase
  include ComponentTestHelper
  include Rails.application.routes.url_helpers

  test "should not catch fire" do
    assert_renders(Views::Accounts::New)
  end

  test "should take optional account param" do
    account = Account.new(name: "Test Account")
    assert_renders(Views::Accounts::New, account: account)
  end
end
