require "test_helper"
require "test_helpers/component_test_helper"

class ViewsProjectsNewTest < ActiveSupport::TestCase
  include ComponentTestHelper

  test "should not catch fire" do
    assert_renders(
      Views::Projects::New,
      project: Project.new(account: accounts(:account))
    )
  end
end
