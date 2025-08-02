require "application_system_test_case"

class AccountsTest < ApplicationSystemTestCase
  setup do
    @account = accounts(:account)
  end

  test "should create account" do
    sign_in_as(users(:user_without_account))

    visit new_account_url
    assert_current_path new_account_path, wait: true

    fill_in t("activerecord.attributes.account.name"), with: "Omni Corp"
    click_on "Create Account"

    assert_text t("accounts.create.success")
  end
end
