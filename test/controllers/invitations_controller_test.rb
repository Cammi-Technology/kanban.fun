require "test_helper"

class InvitationsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = users(:rachel_graves)
    @invited_user = users(:lazaro_nixon)
  end

  test "should get new" do
    get new_invitation_url
    assert_requires_authentication

    sign_in_as @user
    get new_invitation_url
    assert_response :success
  end

  test "should create invitation" do
    sign_in_as @user
    email = @invited_user.email

    assert_enqueued_email_with UserMailer, :invitation_instructions, params: { user: @invited_user } do
      post invitation_url, params: { email: email }
    end

    assert_redirected_to new_invitation_url
    assert_equal "An invitation email has been sent to #{email}", flash[:notice]
  end

  test "should not create invitation with invalid params" do
    sign_in_as @user

    assert_no_enqueued_emails do
      post invitation_url, params: { email: "" }
    end

    assert_response :unprocessable_entity
    assert_select "li", /Email can't be blank/
  end
end
