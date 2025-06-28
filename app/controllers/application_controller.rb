class ApplicationController < ActionController::Base
  include Pundit::Authorization

  # Only allow modern browsers supporting webp images, web push, badges, import maps, CSS nesting, and CSS :has.
  allow_browser versions: :modern

  before_action :set_current_request_details
  before_action :authenticate
  before_action :set_current_account_user

  after_action :verify_pundit_authorization

  layout false

  private
    def authenticate
      if session_record = Session.find_by_id(cookies.signed[:session_token])
        Current.session = session_record
      else
        redirect_to sign_in_path
      end
    end

    def set_current_request_details
      Current.user_agent = request.user_agent
      Current.ip_address = request.ip
    end

    def set_current_account_user
      return unless params[:account_id]

      Current.account_user = AccountUser.find_by!(
        account_id: params[:account_id],
        user_id: Current.user.id
      )
    end

    def verify_pundit_authorization
      verify_policy_scoped
    rescue Pundit::PolicyScopingNotPerformedError
      verify_authorized
    end

    def pundit_user
      Current.user
    end

    def require_sudo
      unless Current.session.sudo?
        redirect_to new_sessions_sudo_path(proceed_to_url: request.original_url)
      end
    end
end
