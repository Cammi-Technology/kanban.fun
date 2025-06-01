module ComponentTestHelper
  # Asserts that the component renders without raising an error.
  #
  # Example:
  #   assert_renders(MyComponent, title: "Hello", user: users(:one))
  #
  # Optionally yields the rendered HTML if you want to do further assertions.
  def assert_renders(component_class, **params)
    html = nil
    assert_nothing_raised do
      html = component_class.new(**params).call
    end
    yield(html) if block_given?
  end
end
