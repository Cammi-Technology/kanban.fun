require "test_helper"
require "test_helpers/component_test_helper"

class NavbarItemTest < ActiveSupport::TestCase
  include ComponentTestHelper
  include Rails.application.routes.url_helpers

  test "should not catch fire" do
    assert_renders(Components::NavbarItem, icon: "house", label: "Home", href: root_path)
  end
end
