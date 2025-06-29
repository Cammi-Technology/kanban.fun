require "test_helper"

class InvitationsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = users(:lazaro_nixon)
    @invitee = users(:rachel_graves)
  end

  test "should get new" do
    get new_invitation_url
    assert_requires_authentication

    sign_in_as(@user)
    get new_invitation_url
    assert_response :success
  end

  test "should create invitation" do
    sign_in_as(@user)

    assert_enqueued_email_with UserMailer, :invitation_instructions, params: { user: @invitee } do
      post invitation_url, params: { email: @invitee.email }
    end

    assert_redirected_to new_invitation_url
    assert_equal I18n.t('invitations.create.success', email: @invitee.email), flash[:notice]
  end

  test "should not create invitation with invalid params" do
    sign_in_as(@user)

    post invitation_url, params: { email: "" }

    assert_response :unprocessable_entity
    assert_includes response.body, "Send invitation"
  end
end
