require "test_helper"

class PasswordsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = users(:lazaro_nixon)
  end

  test "should get edit" do
    sign_in_as @user
    get edit_password_url
    assert_response :success
  end

  test "should not get edit when not signed in" do
    get edit_password_url
    assert_requires_authentication
  end

  test "should update password" do
    sign_in_as @user
    patch password_url, params: { password_challenge: "Secret1*3*5*", password: "Secret6*4*2*", password_confirmation: "Secret6*4*2*" }
    assert_redirected_to root_url
  end

  test "should not update password when not signed in" do
    patch password_url, params: { password_challenge: "Secret1*3*5*", password: "Secret6*4*2*", password_confirmation: "Secret6*4*2*" }
    assert_requires_authentication
  end

  test "should not update password with wrong password challenge" do
    sign_in_as @user
    patch password_url, params: { password_challenge: "SecretWrong1*3", password: "Secret6*4*2*", password_confirmation: "Secret6*4*2*" }

    assert_response :unprocessable_entity
    assert_select "li", /Password challenge is invalid/
  end
end
