require "test_helper"
class PostsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @account = accounts(:account)
    @project = projects(:project)
    @account_owner = users(:account_owner)
    @account_user = users(:account_user)
    @other_users_account = accounts(:other_account)
  end

  # test "should get index when signed in" do
  #   sign_in_as(@account_user)
  #   get account_projects_posts_url(@account, @project)
  #   assert_response :success
  # end
  #
  # test "index should be unauthorized when not signed in" do
  #   get account_projects_url(@account)
  #   assert_requires_authentication
  # end
  #
  # test "should not get other users' projects" do
  #   get account_projects_url(@other_users_account)
  #   refute_includes response.body, @other_users_account.name
  # end

  test "should get index when signed in" do
    get account_project_posts_url(@account, @project)
    assert_requires_authentication

    sign_in_as(@account_user)
    get account_project_posts_url(@account, @project)
    assert_response :success
  end


  # test "should get new when signed in" do
  #   get new_account_project_url(@account)
  #   assert_requires_authentication
  #
  #   sign_in_as(@account_user)
  #   get new_account_project_url(@account)
  #   assert_response :success
  #
  #   get new_account_project_url(@other_users_account)
  #   assert_response :not_found
  # end
  #
  # test "should create project when signed in" do
  #   post account_projects_url(@account)
  #   assert_requires_authentication
  #
  #   sign_in_as(@account_user)
  #   assert_difference -> { @account.reload.projects.count } do
  #     post account_projects_url(@account), params: { project: { name: "New Project" } }
  #   end
  #
  #   assert_redirected_to account_project_url(
  #     @account,
  #     @account.projects.order(id: :desc).limit(1).last
  #   )
  # end
  #
  # test "should not create project with invalid params" do
  #   sign_in_as(@account_owner)
  #
  #   assert_no_difference -> { @account.reload.projects.count } do
  #     post account_projects_url(@account), params: { project: { name: "" } }
  #   end
  #
  #   assert_response :unprocessable_entity
  # end
end
