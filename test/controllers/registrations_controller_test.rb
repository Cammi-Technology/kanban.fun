require "test_helper"

class RegistrationsControllerTest < ActionDispatch::IntegrationTest
  test "should get new" do
    get sign_up_url
    assert_response :success
  end

  test "should sign up" do
    assert_difference("User.count") do
      post sign_up_url, params: {
        email: "lazaronixon@hey.com",
        password: "Secret1*3*5*",
        password_confirmation: "Secret1*3*5*",
        first_name: "Lazaro",
        last_name: "Nixon"
      }
    end

    assert_redirected_to root_url
  end

  test "should send welcome email" do
    skip "not yet implemented"
  end
end
