require "test_helper"

class CommentsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @account = accounts(:account)
    @project = projects(:project)
    @post = posts(:post)
    @comment = comments(:comment)
    @account_user = users(:account_user)
    @other_users_account = accounts(:other_account)
    @other_accounts_project = projects(:other_accounts_project)
    @other_accounts_post = posts(:other_users_post)
  end

  test "create should be unauthorized when not signed in" do
    post account_project_post_comments_url(@account, @project, @post)
    assert_requires_authentication
  end

  test "destroy should be unauthorized when not signed in" do
    delete account_project_post_comment_url(@account, @project, @post, @comment)
    assert_requires_authentication
  end

  test "should create comment when signed in" do
    sign_in_as(@account_user)

    assert_difference -> { @post.reload.comments.count } do
      post(
        account_project_post_comments_url(@account, @project, @post),
        params: { comment: { content: "<b>foo</b>" } }
      )
    end

    assert_redirected_to account_project_post_url(@account, @project, @post)
  end

  test "should not create comment with invalid params" do
    sign_in_as(@account_user)

    assert_no_difference -> { @post.reload.comments.count } do
      post account_project_post_comments_url(@account, @project, @post), params: { comment: { content: "" } }
    end

    assert_response :unprocessable_entity
  end

  test "should destroy comment when signed in" do
    sign_in_as(@account_user)

    assert_difference -> { @post.reload.comments.count }, -1 do
      delete account_project_post_comment_url(@account, @project, @post, @comment)
    end

    assert_redirected_to account_project_post_url(@account, @project, @post)
  end

  test "should not access other accounts' project or post" do
    sign_in_as(@account_user)

    post(
      account_project_post_comments_url(@other_users_account, @other_accounts_project, @other_accounts_post),
      params: { comment: { content: "Foo" } }
    )
    assert_response :not_found

    other_comment = Comment.create!(
      author: account_users(:other_account_owner),
      commentable: @other_accounts_post,
      content: "Bar"
    )

    delete account_project_post_comment_url(@other_users_account, @other_accounts_project, @other_accounts_post, other_comment)
    assert_response :not_found
  end
end
