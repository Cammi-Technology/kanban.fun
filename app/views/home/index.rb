# frozen_string_literal: true

class Views::Home::Index < Views::Base
  include Phlex::Rails::Helpers::ButtonTo
  include Phlex::Rails::Helpers::LinkTo
  include Phlex::Rails::Helpers::Routes
  include Phlex::Rails::Helpers::Notice

  def page_title = "Home"

  def view_template
    p(style: "color:#008000") { notice }

    p do
      plain "Signed as "
      plain Current.user.email
    end

    h2 { "Login and verification" }

    div do
      link_to "Change password", edit_password_path
    end

    div do
      link_to "Change email address", edit_identity_email_path
    end

    h2 { "Access history" }
    div do
      link_to "Devices & Sessions", sessions_path
    end

    br

    button_to "Log out", Current.session, method: :delete
  end
end
