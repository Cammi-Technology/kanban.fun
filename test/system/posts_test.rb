require "application_system_test_case"

class PostsTest < ApplicationSystemTestCase
  setup do
    @account_owner = users(:account_owner)
    @account = accounts(:account)
    @project = projects(:project)
  end

  test "should create post" do
    sign_in_as(@account_owner)
    assert_current_path accounts_path, wait: true

    visit new_account_project_post_url(@account, @project)
    assert_current_path new_account_project_post_path(@account, @project), wait: true

    fill_in t("activerecord.attributes.post.title"), with: "Nuke Initiative for increasing crime in Detroit City"
    fill_in_rich_text_area "post_content", with: "Info about Nuke Initiative"

    click_on "Post this message"
    save_and_open_screenshot
    assert_current_path account_project_post_path(@account, @project, Post.last), wait: true
    assert_text t("posts.create.success")
    assert_text "Nuke Initiative for increasing crime in Detroit City"
    assert_text "Info about Nuke Initiative"

    visit account_project_posts_url(@account, @project)
    assert_text "Nuke Initiative for increasing crime in Detroit City"
  end
end
