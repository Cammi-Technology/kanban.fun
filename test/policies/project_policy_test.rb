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
    @other_account_user = AuthorizationContext.new(
      user: users(:other_account_owner),
      account_user: account_users(:other_account_owner)
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

  def test_visit_new
    assert_permit(@user, @account.projects.new, :new)
    refute_permit(@other_account_user, @account.projects.new, :new)
  end

  def test_create
    assert_permit(@user, @account.projects.new, :create)
    refute_permit(@other_account_user, @account.projects.new, :create)
  end

  def test_show
    assert_permit(@user, @project, :show)
    refute_permit(@other_account_user, @project, :show)
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
