require "test_helper"
class ProjectPolicyTest < ActiveSupport::TestCase
  def setup
    @account = accounts(:account)
    @project = projects(:project)
    @other_accounts_project = projects(:other_accounts_project)
    @account_user = account_users(:account_owner)
    @other_account_user = account_users(:other_account_owner)
  end

  def test_scope
    assert_includes(
      ProjectPolicy::Scope.new(@account_user, Project).resolve,
      @project
    )
    refute_includes(
      ProjectPolicy::Scope.new(@account_user, Project).resolve,
      @other_accounts_project
    )
  end

  def test_visit_index
    assert_permit(@account_user, Project, :index)
  end

  def test_visit_new
    assert_permit(@account_user, @account.projects.new, :new)
    refute_permit(@other_account_user, @account.projects.new, :new)
  end

  def test_create
    assert_permit(@account_user, @account.projects.new, :create)
    refute_permit(@other_account_user, @account.projects.new, :create)
  end

  def test_show
    assert_permit(@account_user, @project, :show)
    refute_permit(@other_account_user, @project, :show)
  end

  def test_requires_account_user
    user = users(:rachel_graves)

    assert_raises(Literal::TypeError) do
      ProjectPolicy.new(user, @project).new?
    end

    assert_raises(Literal::TypeError) do
      ProjectPolicy.new(user, Project).index?
    end
  end

  def test_set_current_project
    assert_permit(@account_user, @project, :set_current_project)
    refute_permit(@other_account_user, @project, :set_current_project)
  end
end
