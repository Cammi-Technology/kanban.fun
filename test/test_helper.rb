ENV["RAILS_ENV"] ||= "test"
require_relative "../config/environment"
require "rails/test_help"
require "minitest/reporters"
require "test_helpers/authentication_helper"
require "test_helpers/authorization_helper"

Minitest::Reporters.use! Minitest::Reporters::SpecReporter.new(print_failure_summary: true, suppress_inline_failure_output: true)
Minitest.backtrace_filter = Minitest::BacktraceFilter.new

class ActiveSupport::TestCase
  include AuthenticationHelper
  include AuthorizationHelper

  # Run tests in parallel with specified workers
  parallelize(workers: :number_of_processors)

  # Setup all fixtures in test/fixtures/*.yml for all tests in alphabetical order.
  fixtures :all

  # Add more helper methods to be used by all tests here...
  def sign_in_as(user)
    post(sign_in_url, params: { email: user.email, password: "Secret1*3*5*" }); user
  end
end
