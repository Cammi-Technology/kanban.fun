require "test_helper"

class ApplicationRedirectionTest < ActionDispatch::IntegrationTest
  setup do
    @user = users(:account_user)
    @account = accounts(:cammi)
  end

  test "redirects to last viewed account" do
    sign_in_as(@user)
    @user.update!(last_viewed_account: @account)

    get root_url
    assert_redirected_to account_dashboard_url(@account)
  end

  test "redirects to first account if no last viewed" do
    sign_in_as(@user)

    get root_url
    assert_redirected_to account_dashboard_url(@account)
  end
end
