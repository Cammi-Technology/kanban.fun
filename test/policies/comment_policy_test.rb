require "test_helper"

class CommentPolicyTest < ActiveSupport::TestCase
  def setup
    @account = accounts(:account)
    @post = posts(:post)
    @comment = comments(:comment)
    @account_user = account_users(:account_owner)
    @other_account_user = account_users(:other_account_owner)
    @other_accounts_post = posts(:other_users_post)
    @other_accounts_comment = Comment.create!(
      author: @other_account_user,
      commentable: @other_accounts_post,
      content: "Other"
    )
  end

  def test_scope
    assert_includes(
      CommentPolicy::Scope.new(@account_user, Comment).resolve,
      @comment
    )
    refute_includes(
      CommentPolicy::Scope.new(@account_user, Comment).resolve,
      @other_accounts_comment
    )
  end

  def test_create
    assert_permit(
      @account_user,
      @post.comments.new(author: @account_user, content: "Hi"),
      :create
    )
    refute_permit(
      @other_account_user,
      @post.comments.new(author: @other_account_user, content: "Hi"),
      :create
    )
  end

  def test_destroy
    assert_permit(@account_user, @comment, :destroy)
    refute_permit(@other_account_user, @comment, :destroy)
  end
end
