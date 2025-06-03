require 'test_helper'

class UserPolicyTest < ActiveSupport::TestCase
  def test_update_email
    user = users(:rachel_graves)

    assert_permit user, user, :update_email
  end
end
