require "test_helper"

class PageInfoTest < ActiveSupport::TestCase
  test "should have a title" do
    assert_equal(PageInfo.new(title: "Test").title, "Test")
  end
end
