require "test_helper"
require "test_helpers/component_test_helper"

class CommentFormTest < ActiveSupport::TestCase
  include ComponentTestHelper
  include Rails.application.routes.url_helpers

  setup do
    @account = accounts(:account)
    @project = projects(:project)
    @post = posts(:post)

    Current.stubs(:account).returns(@account)
    Current.stubs(:project).returns(@project)
  end

  test "renders form for new comment" do
    assert_renders(Components::CommentForm, record: @post) do |html|
      assert_includes html, "trix-editor"
      assert_includes html, "data-controller=\"mentions\""
      assert_includes html, "Add Comment"
      assert_includes html, "data-mentions-target=\"input\""
    end
  end

  test "renders form for existing comment" do
    comment = Comment.new(record: @post, content: "Existing content")

    assert_renders(Components::CommentForm, record: @post, comment: comment) do |html|
      assert_includes html, "trix-editor"
      assert_includes html, "Update Comment"
    end
  end

  test "includes mentions data attributes" do
    assert_renders(Components::CommentForm, record: @post) do |html|
      assert_includes html, "data-controller=\"mentions\""
      assert_includes html, "data-mentions-target=\"input\""
      assert_includes html, "data-mentions-url-value="
    end
  end

  test "renders without errors" do
    assert_renders(Components::CommentForm, record: @post)
  end
end
