require "test_helper"
require "test_helpers/component_test_helper"

class QuickActionTileComponentTest < ActiveSupport::TestCase
  include ComponentTestHelper

  test "should not catch fire" do
    assert_renders(
      Components::QuickActionTile,
      href: "/projects/1/posts",
      icon: :file_post,
      label: "Posts"
    )
  end
end
