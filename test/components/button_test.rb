require "test_helper"
require "test_helpers/component_test_helper"

class ButtonTest < ActiveSupport::TestCase
  include ComponentTestHelper
  include Rails.application.routes.url_helpers

  test "should not catch fire" do
    assert_renders(
      Components::Button,
      id: "name",
      class: "button--accent"
    )
  end
end
