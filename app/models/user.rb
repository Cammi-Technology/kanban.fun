class User < ApplicationRecord
  has_secure_password
  has_person_name

  belongs_to :last_viewed_account, class_name: "Account", optional: true
  has_many :account_users
  has_many :accounts, through: :account_users
  has_many :owned_accounts, class_name: "Account", foreign_key: "owner_id"

  generates_token_for :email_verification, expires_in: 2.days do
    email
  end

  generates_token_for :password_reset, expires_in: 20.minutes do
    password_salt.last(10)
  end


  has_many :sessions, dependent: :destroy

  validates :email, presence: true, uniqueness: true, format: { with: URI::MailTo::EMAIL_REGEXP }
  validates :password, allow_nil: true, length: { minimum: 8 }

  normalizes :email, with: -> { _1.strip.downcase }

  before_validation if: :email_changed?, on: :update do
    self.verified = false
  end

  after_update if: :password_digest_previously_changed? do
    sessions.where.not(id: Current.session).delete_all
  end
end
