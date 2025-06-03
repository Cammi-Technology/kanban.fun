require "test_helper"
require "test_helpers/authorization_helper"

class SessionPolicyTest < ActiveSupport::TestCase
  include AuthorizationHelper

  def setup
    @user = users(:rachel_graves)
    @signed_in_user = users(:signed_in_user)
    @signed_in_users_session = sessions(:one)
    @other_users_session = sessions(:two)
  end

  def test_index
    assert_permit(@signed_in_user, Session, :index)
  end

  def test_new
    assert_permit(@user, Session.new, :new)
  end

  def test_destroy
    assert_permit(@signed_in_user, @signed_in_users_session, :destroy)
    refute_permit(@signed_in_user, @other_users_session, :destroy)
  end

  def test_scope
    refute_includes(
      SessionPolicy::Scope.new(@user, Session.all).resolve,
      @other_session
    )
  end
end
