require "test_helper"

class ApplicationSystemTestCase < ActionDispatch::SystemTestCase
  driven_by :selenium, using: :headless_chrome, screen_size: [ 1400, 1400 ]

  def sign_in_as(user)
    visit sign_in_url
    fill_in "Email", with: user.email
    fill_in "Password", with: "Secret1*3*5*"
    click_on "Sign in"

    if user.accounts.any?
      assert_current_path accounts_path, wait: true
    else
      assert_current_path new_account_path, wait: true
    end
  end
end
