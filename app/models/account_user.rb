class AccountUser < ApplicationRecord
  include ActionText::Attachable

  belongs_to :account
  belongs_to :user

  delegate :name, :first_name, :last_name, to: :user

  def to_attachable_partial_path
    "account_users/mention"
  end

  def to_trix_content_attachment_partial_path
    "account_users/mention"
  end
end
