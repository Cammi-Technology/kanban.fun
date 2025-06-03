class EmailVerificationPolicy < ApplicationPolicy
  prop :record, User, :positional, reader: :public

  def create? = true
end
