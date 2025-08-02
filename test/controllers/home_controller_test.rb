require "test_helper"

class HomeControllerTest < ActionDispatch::IntegrationTest
  test "should get index" do
    get root_url

    assert_requires_authentication
  end

  test "should redirect to accounts path when user is signed in" do
    sign_in_as users(:rachel_graves)

    get root_url

    assert_redirected_to accounts_path
  end
end
