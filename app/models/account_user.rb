class AccountUser < ApplicationRecord
  include ActionText::Attachable

  belongs_to :account
  belongs_to :user

  delegate :name, :first_name, :last_name, to: :user
end
