require "test_helper"
require "test_helpers/component_test_helper"

class FormLabelTest < ActiveSupport::TestCase
  include ComponentTestHelper

  test "should not catch fire" do
    assert_renders(
      Components::FormLabel,
      for: "accounts[name]"
    )
  end
end
