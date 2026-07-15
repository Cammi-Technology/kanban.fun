require "test_helper"
require "test_helpers/component_test_helper"

class ProjectDropdownComponentTest < ActiveSupport::TestCase
  include ComponentTestHelper
  include Rails.application.routes.url_helpers

  setup do
    @account = accounts(:account)
    @project = projects(:project)
    @post = posts(:post)
    @other_project = @account.projects.create!(name: "Second Project")

    Current.stubs(:user).returns(users(:account_owner))
    Current.stubs(:account).returns(@account)
    Current.stubs(:project).returns(@project)
  end

  test "should not catch fire" do
    assert_renders(
      Components::ProjectDropdown,
      projects: Project.where(id: @project.id)
    )
  end

  test "marks the current project in the dialog" do
    fragment = render_fragment(
      Components::ProjectDropdown.new(
        projects: Project.where(id: [ @project.id, @other_project.id ])
      )
    )

    assert fragment.at_css("a[aria-current='page']")
  end

  test "uses project params when Current.project is not set" do
    Current.stubs(:project).returns(nil)

    component = Components::ProjectDropdown.new(
      projects: Project.where(id: [ @project.id, @other_project.id ])
    )
    component.stubs(:params).returns(
      ActionController::Parameters.new(controller: "projects", id: @project.id)
    )

    fragment = render_fragment(component)
    current_link = fragment.at_css("a[aria-current='page']")
    current_title = current_link.at_css(".project-dropdown__link-title")

    assert_equal @project.name, current_title.text.strip
    assert_equal account_project_path(@account, @project), current_link["href"]
  end
end
