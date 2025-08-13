require "test_helper"
require "test_helpers/component_test_helper"

class ViewsPostsShowTest < ActiveSupport::TestCase
  include ComponentTestHelper
  include Rails.application.routes.url_helpers

  setup do
    @account = accounts(:account)
    @project = projects(:project)

    Current.stubs(:account).returns(@account)
    Current.stubs(:project).returns(@project)
  end

  test "should not catch fire" do
    assert_renders(Views::Posts::Show, post: posts(:post))
  end
end
