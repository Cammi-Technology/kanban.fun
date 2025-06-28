class Current < ActiveSupport::CurrentAttributes
  attribute :session
  attribute :user_agent, :ip_address
  attribute :account_user
  attribute :account

  delegate :user, to: :session, allow_nil: true
end
