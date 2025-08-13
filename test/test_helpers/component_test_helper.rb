module ComponentTestHelper
  def render(*args, **kwargs, &block)
    view_context.render(*args, **kwargs, &block)
  end

  def view_context
    controller.view_context
  end

  def controller
    @controller ||= begin
      controller = ActionView::TestCase::TestController.new
      controller.class.include Pundit::Authorization
      controller.define_singleton_method(:pundit_user) { Current.account_user || Current.user }
      controller
    end
  end

  # Asserts that the component renders without raising an error.
  #
  # Example:
  #   assert_renders(MyComponent, title: "Hello", user: users(:one))
  #
  # Optionally yields the rendered HTML if you want to do further assertions.
  def assert_renders(component_class, **params, &)
    html = nil
    assert_nothing_raised do
      html = render(component_class.new(**params, &))
    end
    yield(html) if block_given?
  end
end
