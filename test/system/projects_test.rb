require "application_system_test_case"

class ProjectsTest < ApplicationSystemTestCase
  setup do
    @account_owner = users(:account_owner)
    @account = accounts(:account)
  end

  test "account owner can create project" do
    sign_in_as(@account_owner)

    visit new_account_project_url(@account)
    assert_current_path new_account_project_path(@account), wait: true

    fill_in t("activerecord.attributes.project.name"), with: "Redevelop Detroit City into Delta City"
    fill_in t("placeholders.project.description"), with: "Delta City: 'For Our Children!'"

    click_on "Create Project"

    assert_text t("projects.create.success")
    assert_text "Redevelop Detroit City into Delta City"

    visit account_projects_url(@account)
    assert_text "Redevelop Detroit City into Delta City"
  end
end
