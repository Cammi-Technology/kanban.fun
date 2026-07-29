require "test_helper"
require "test_helpers/component_test_helper"

class AvatarComponentTest < ActiveSupport::TestCase
  include ComponentTestHelper

  test "should not catch fire" do
    assert_renders(Components::Avatar, name: "Rachel Graves")
  end
end
