module AuthenticationHelper
  def assert_requires_authentication(message = nil)
    assert_response :redirect, message
    assert_redirected_to sign_in_url, message
  end
end
