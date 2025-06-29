require "test_helper"

class PageInfoTest < ActiveSupport::TestCase
  test "should have a title" do
    assert_equal(PageInfo.new(title: "Test").title, "Test")
  end

  test "should have a flash" do
    flash = ActionDispatch::Flash::FlashHash.new
    flash[:notice] = "You are signed in"

    assert_equal(
      PageInfo.new(title: "Test", flash: flash).flash, flash
    )
  end
end
