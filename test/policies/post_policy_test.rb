require "test_helper"

class PostPolicyTest < ActiveSupport::TestCase
  def setup
    @account = accounts(:account)
    @post = posts(:post)
    @project = projects(:project)
    @other_accounts_post = posts(:other_users_post)
    @account_user = account_users(:account_user)
    @other_account_user = account_users(:other_account_owner)
    @account_owner_user = account_users(:account_owner)
  end

  def test_scope
    assert_includes(
      PostPolicy::Scope.new(@account_user, Post).resolve,
      @post
    )
    refute_includes(
      PostPolicy::Scope.new(@account_user, Post).resolve,
      @other_accounts_post
    )
  end

  def test_visit_index
    assert_permit(@account_user, Post, :index)
  end

  def test_visit_new
    assert_permit(@account_user, @project.posts.new, :new)
    refute_permit(@other_account_user, @project.posts.new, :new)
  end

  def test_create
    assert_permit(@account_user, @project.posts.new, :create)
    refute_permit(@other_account_user, @project.posts.new, :create)
  end

  def test_show
    assert_permit(@account_user, @post, :show)
    refute_permit(@other_account_user, @post, :show)
  end

  def test_edit
    # Author can edit their own post
    assert_permit(@account_user, @post, :edit)

    # Different user in same account cannot edit someone else's post
    refute_permit(@account_owner_user, @post, :edit)

    # User from different account cannot edit
    refute_permit(@other_account_user, @post, :edit)
  end

  def test_update
    # Author can update their own post
    assert_permit(@account_user, @post, :update)

    # Different user in same account cannot update someone else's post
    refute_permit(@account_owner_user, @post, :update)

    # User from different account cannot update
    refute_permit(@other_account_user, @post, :update)
  end
end
