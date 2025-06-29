require "test_helper"

class UserPolicyTest < ActiveSupport::TestCase
  def setup
    @user = users(:rachel_graves)
  end

  def test_visit_home
    assert_permit @user, @user, :visit_home
  end

  def test_edit_email
    assert_permit @user, @user, :edit_email
  end

  def test_update_email
    assert_permit @user, @user, :update_email
  end

  def test_create_email_verification
    assert_permit @user, @user, :create_email_verification
  end

  def test_edit_password
    assert_permit @user, @user, :edit_password
  end

  def test_update_password
    assert_permit @user, @user, :update_password
  end
end
