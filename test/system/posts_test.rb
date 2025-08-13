require "application_system_test_case"

class PostsTest < ApplicationSystemTestCase
  setup do
    @account_owner = users(:account_owner)
    @account = accounts(:account)
    @project = projects(:project)
  end

  test "should create post" do
    sign_in_as(@account_owner)

    click_on @account.name
    assert_current_path account_dashboard_path(@account), wait: true

    click_on @project.name
    assert_current_path account_project_path(@account, @project), wait: true

    click_on t("views.projects.show.posts")
    assert_current_path account_project_posts_path(@account, @project), wait: true

    click_on t("views.posts.index.new")
    assert_current_path new_account_project_post_path(@account, @project), wait: true

    fill_in t("activerecord.attributes.post.title"), with: "Nuke Initiative for increasing crime in Detroit City"
    fill_in_rich_text_area "post_content", with: "Info about Nuke Initiative"

    click_on "Post this message"

    assert_text t("posts.create.success")
    assert_current_path account_project_post_path(@account, @project, Post.order(created_at: :asc).last), wait: true
    assert_text "Nuke Initiative for increasing crime in Detroit City"
    assert_text "Info about Nuke Initiative"

    visit account_project_posts_url(@account, @project)
    assert_text "Nuke Initiative for increasing crime in Detroit City"
  end

  test "should display comment form on post show page" do
    sign_in_as(@account_owner)

    post = posts(:post)
    visit account_project_post_path(@account, @project, post)

    assert_text "Comments"
    assert_selector "form[action*='comments']"
    assert_selector "trix-editor"
    assert_button "Add Comment"
  end

  test "should create comment on post" do
    sign_in_as(@account_owner)

    post = posts(:post)
    visit account_project_post_path(@account, @project, post)

    fill_in_rich_text_area "comment_content", with: "This is a test comment"
    click_on "Add Comment"

    # Verify success notice appears
    assert_text t("comments.create.success"), wait: true
    # Now verify comment is displayed
    assert_text "This is a test comment"
  end

  test "should edit post when author" do
    sign_in_as(users(:account_user))

    post = posts(:post)
    visit account_project_post_path(@account, @project, post)

    # Edit link should be visible for the author
    assert_text "Edit"
    click_on "Edit"

    assert_current_path edit_account_project_post_path(@account, @project, post), wait: true

    # Update the post
    fill_in t("activerecord.attributes.post.title"), with: "Updated Post Title"
    fill_in_rich_text_area "post_content", with: "Updated post content"

    click_on "Post this message"

    # Verify redirect and success message
    assert_text t("posts.update.success")
    assert_current_path account_project_post_path(@account, @project, post), wait: true
    assert_text "Updated Post Title"
    assert_text "Updated post content"
  end

  test "should not show edit link to non-author" do
    sign_in_as(users(:account_owner))  # Different from post author

    post = posts(:post)  # This post is authored by account_user, not account_owner
    visit account_project_post_path(@account, @project, post)

    # Edit link should not be visible for non-authors
    assert_no_text "Edit"
  end
end
