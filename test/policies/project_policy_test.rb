require "test_helper"
class ProjectPolicyTest < ActiveSupport::TestCase
  def setup
    @account = accounts(:account)
    @project = projects(:project)
    @other_accounts_project = projects(:other_accounts_project)
    @user = AuthorizationContext.new(
      user: users(:account_owner),
      account_user: account_users(:account_owner)
    )
  end

  def test_scope
    assert_includes(
      ProjectPolicy::Scope.new(@user, Project).resolve,
      @project
    )
    refute_includes(
      ProjectPolicy::Scope.new(@user, Project).resolve,
      @other_accounts_project
    )
  end

  def test_visit_index
    assert_permit(@user, Project, :index)
  end

  def test_requires_account_user
    authorization_context_without_user = AuthorizationContext.new(user: users(:rachel_graves), account_user: nil)

    assert_raises(Literal::TypeError) do
      ProjectPolicy.new(authorization_context_without_user, @project).new?
    end

    assert_raises(Literal::TypeError) do
      ProjectPolicy.new(authorization_context_without_user, Project).index?
    end
  end
end
