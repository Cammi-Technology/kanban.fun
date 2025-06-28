require "application_system_test_case"

class AccountsTest < ApplicationSystemTestCase
  setup do
    @account = accounts(:account)
  end

  test "visiting the index" do
    visit accounts_url
    assert_selector "h1", text: "Accounts"
  end

  test "should create account" do
    sign_in_as(users(:user_without_account))

    visit new_account_url
    fill_in t("activerecord.attributes.account.name"), with: "Omni Corp"
    click_on "Create Account"

    assert_text t("accounts.create.success")
  end

  test "should update Account" do
    visit account_url(@account)
    click_on "Edit this account", match: :first

    fill_in "Name", with: "Kanemitsu Corporation"
    click_on "Update Account"

    assert_text "Account was successfully updated"
  end

  test "should destroy Account" do
    visit account_url(@account)
    click_on "Destroy this account", match: :first

    assert_text "Account was successfully destroyed"
  end
end
