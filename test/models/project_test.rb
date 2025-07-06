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
end
