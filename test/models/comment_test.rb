require "test_helper"

class CommentTest < ActiveSupport::TestCase
  def setup
    @comment = Comment.new
    @comment.valid?
  end

  test "requires author" do
    assert @comment.errors.of_kind? :author, :blank
  end

  test "requires content" do
    assert @comment.errors.of_kind? :content, :blank
  end

  test "belongs to author" do
    assert_equal comments(:comment).author, account_users(:account_user)
  end

  test "belongs to record" do
    assert_equal comments(:comment).record, posts(:post)
  end
end
