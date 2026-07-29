require "test_helper"
require "test_helpers/component_test_helper"

class ContentShellComponentTest < ActiveSupport::TestCase
  include ComponentTestHelper

  test "renders a wide shell by default" do
    shell = Nokogiri::HTML5.fragment(
      render(Components::ContentShell.new) { "Hello" }
    ).at_css("div")

    assert_equal [ "content-shell", "content-shell--wide" ], shell["class"].split
    assert_equal "Hello", shell.text
  end

  test "renders a narrow shell" do
    shell = render_fragment(Components::ContentShell.new(width: :narrow)).at_css("div")

    assert_equal [ "content-shell", "content-shell--narrow" ], shell["class"].split
  end
end
