require 'test_helper'

class EmailVerificationPolicyTest < ActiveSupport::TestCase
  def test_create
    user = users(:rachel_graves)

    assert EmailVerificationPolicy.new(user, user).create?
  end
end
