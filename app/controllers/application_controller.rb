class ApplicationController < ActionController::Base
  include Pundit::Authorization

  # Only allow modern browsers supporting webp images, web push, badges, import maps, CSS nesting, and CSS :has.
  allow_browser versions: :modern

  before_action :set_current_request_details
  before_action :authenticate
  before_action :redirect_to_account
  before_action :set_current_account_user

  after_action :store_last_viewed_account

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

    def redirect_to_account
      return unless should_redirect_to_account?

      account = last_viewed_or_first_account
      redirect_to account_dashboard_path(account) if account
    end

    def should_redirect_to_account?
      Current.user.present? && !params[:account_id] && !authentication_controller?
    end

    def last_viewed_or_first_account
      account = Current.user.last_viewed_account
      account ||= Current.user.accounts.first
      account
    end

    def authentication_controller?
      controller_path.start_with?("sessions") ||
        controller_path.start_with?("registrations") ||
        controller_path.start_with?("identity/") ||
        controller_path.start_with?("passwords")
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

  def store_last_viewed_account
    return unless Current.account_user

    if Current.user.last_viewed_account_id != Current.account_user.account_id
      Current.user.update(last_viewed_account_id: Current.account_user.account_id)
    end
  end

    def verify_pundit_authorization
      verify_policy_scoped
    rescue Pundit::PolicyScopingNotPerformedError
      verify_authorized
    end

    def pundit_user
      Current.user
    end
end
