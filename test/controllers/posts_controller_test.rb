require "test_helper"
class PostsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @account = accounts(:account)
    @project = projects(:project)
    @account_owner = users(:account_owner)
    @account_user = users(:account_user)
    @other_users_account = accounts(:other_account)
    @other_accounts_project = projects(:other_accounts_project)
  end

  test "index should be unauthorized when not signed in" do
    get account_project_posts_url(@account, @project)
    assert_requires_authentication
  end

   test "should not get other accounts' posts" do
     sign_in_as(@account_user)
     get account_project_posts_url(@other_users_account, @other_accounts_project)
     assert_response :not_found
   end

  test "should get index when signed in" do
    get account_project_posts_url(@account, @project)
    assert_requires_authentication

    sign_in_as(@account_user)
    get account_project_posts_url(@account, @project)
    assert_response :success
  end

  test "should get new when signed in" do
    get new_account_project_post_url(@account, @project)
    assert_requires_authentication

    sign_in_as(@account_user)
    get new_account_project_post_url(@account, @project)
    assert_response :success

    get new_account_project_url(@other_users_account, @other_accounts_project)
    assert_response :not_found
  end

  test "should create post when signed in" do
    post account_project_posts_url(@account, @project)
    assert_requires_authentication

    sign_in_as(@account_user)
    assert_difference -> { @project.reload.posts.count } do
      post(
       account_project_posts_url(@account, @project),
       params: { post: {
         title: "New Post", content: "<b>foo</b>", published: "true" }
       }
      )
    end

    assert_redirected_to account_project_post_url(
      @account,
      @project,
      Post.last
    )
  end

  test "should not create post with invalid params" do
    sign_in_as(@account_owner)

    assert_no_difference -> { @project.reload.posts.count } do
      post account_project_posts_url(@account, @project), params: { post: { title: "New Post" } }
    end

    assert_response :unprocessable_entity
  end

  test "should get show when signed in" do
    get account_project_post_url(@account, @project, posts(:post))
    assert_requires_authentication

    sign_in_as(@account_user)
    get account_project_post_url(@account, @project, posts(:post))
    assert_response :success

    get account_project_post_url(@other_users_account, @other_accounts_project, posts(:post))
    assert_response :not_found
  end
end
