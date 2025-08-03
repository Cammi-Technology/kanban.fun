require "test_helper"

class AccountUsersControllerTest < ActionDispatch::IntegrationTest
  test "should list users in the current account" do
    get account_project_account_users_path(accounts(:account), projects(:project), format: :json)

    assert_response :unauthorized

    sign_in_as users(:account_user)
    get account_project_account_users_path(accounts(:account), projects(:project), format: :json)

    assert_response :success

    body = JSON.parse(response.body)

    assert_equal 2, body.length
    assert_equal users(:account_user).name, body[0]["name"]
  end
end
