require "test_helper"
require "test_helpers/component_test_helper"

class ViewsProjectsShowTest < ActiveSupport::TestCase
  include ComponentTestHelper

  test "should not catch fire" do
    assert_renders(Views::Projects::Show, project: projects(:project))
  end
end
