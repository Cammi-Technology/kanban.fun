require "test_helper"
require "test_helpers/component_test_helper"

class FormRichTextareaTest < ActiveSupport::TestCase
  include ComponentTestHelper
  include Rails.application.routes.url_helpers

  test "should not catch fire" do
    assert_renders(
      Components::FormRichTextarea,
      name: "accounts[content]",
      id: "accounts_content",
      required: true,
      class: "input--accent",
      value: ActionText::RichText.new(body: "<p>Test content</p>")
    )
  end
end
