require "test_helper"
require "test_helpers/component_test_helper"

class ViewsPostsNewTest < ActiveSupport::TestCase
  include ComponentTestHelper
  # include Rails.application.routes.url_helpers

  test "should not catch fire" do
    assert_renders(Views::Posts::New, post: Post.new(project: projects(:project)))
  end
end
