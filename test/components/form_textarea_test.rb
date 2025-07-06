require "test_helper"
require "test_helpers/component_test_helper"

class FormTextareaTest < ActiveSupport::TestCase
  include ComponentTestHelper
  include Rails.application.routes.url_helpers

  test "should not catch fire" do
    assert_renders(
      Components::FormTextarea,
      name: "accounts[name]",
      id: "name",
      required: true,
      class: "input--accent"
    )
  end
end
