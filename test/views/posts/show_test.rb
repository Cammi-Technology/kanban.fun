require "test_helper"
require "test_helpers/component_test_helper"

class ViewsPostsShowTest < ActiveSupport::TestCase
  include ComponentTestHelper
  include Rails.application.routes.url_helpers

  setup do
    @account = accounts(:account)
    @project = projects(:project)
    @account_user = account_users(:account_user)

    Current.stubs(:account).returns(@account)
    Current.stubs(:project).returns(@project)
    Current.stubs(:account_user).returns(@account_user)
  end

  test "should not catch fire" do
    assert_renders(Views::Posts::Show, post: posts(:post))
  end
end
