require "test_helper"

class Identity::EmailsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = users(:lazaro_nixon)
  end

  test "should get edit" do
    sign_in_as @user
    get edit_identity_email_url
    assert_response :success
  end

  test "should not get edit when not signed in" do
    get edit_identity_email_url
    assert_requires_authentication
  end

  test "should update email" do
    sign_in_as @user
    patch identity_email_url, params: { email: "new_email@hey.com", password_challenge: "Secret1*3*5*" }
    assert_redirected_to root_url
  end

  test "should not update email with wrong password challenge" do
    sign_in_as @user
    patch identity_email_url, params: { email: "new_email@hey.com", password_challenge: "SecretWrong1*3" }

    assert_response :unprocessable_content
    assert_select "li", /Password challenge is invalid/
  end

  test "should not update email when not signed in" do
    assert_no_changes -> { @user.reload } do
      patch identity_email_url, params: { email: "new_email@hey.com", password_challenge: "SecretWrong1*3" }
    end

    assert_requires_authentication
  end
end
