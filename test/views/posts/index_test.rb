require "test_helper"
require "test_helpers/component_test_helper"

class ViewsPostsIndexTest < ActiveSupport::TestCase
  include ComponentTestHelper

  test "should not catch fire" do
    Current.stubs(:account).returns(accounts(:account))
    Current.stubs(:project).returns(projects(:project))

    assert_renders(Views::Posts::Index, posts: Post.all)
  end
end
