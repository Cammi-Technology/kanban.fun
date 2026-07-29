require "test_helper"
require "test_helpers/component_test_helper"

class ContentShellComponentTest < ActiveSupport::TestCase
  include ComponentTestHelper

  test "should not catch fire" do
    assert_renders(Components::ContentShell) { "Hello" }
  end
end
