require "test_helper"

class ProjectTest < ActiveSupport::TestCase
  setup do
    @project = Project.new
    @project.valid?
  end

  test "should require name" do
    assert @project.errors.of_kind? :name, :blank
  end

  test "should require account" do
    assert @project.errors.of_kind? :account, :blank
  end

  test "should have many posts" do
    project = projects(:project)

    assert_includes project.posts, posts(:post)
    refute_includes project.posts, posts(:other_users_post)
  end
end
