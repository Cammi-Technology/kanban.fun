require "test_helper"

class PostTest < ActiveSupport::TestCase
  def setup
    @post = Post.new
    @post.valid?
  end

  test "should belong to project" do
    assert_equal posts(:post).project, projects(:project)
  end

  test "should require author" do
    assert @post.errors.of_kind? :author, :blank
  end

  test "should belong to author" do
    assert_equal posts(:post).author, account_users(:account_user)
  end

  test "should require title" do
    assert @post.errors.of_kind? :title, :blank
  end

  test "should require account" do
    assert @post.errors.of_kind? :project, :blank
  end

  test "should require published" do
    @post.published = nil
    @post.valid?
    assert @post.errors.of_kind? :published, :blank
  end

  test "should notify folks when created" do
    assert_changes -> { Noticed::Notification.count } do
      @post.title = "Hello World"
      @post.content = "<p>Content</p>"
      @post.author = account_users(:account_user)
      @post.project = projects(:project)
      @post.published = true
      @post.save!
    end
  end
end
