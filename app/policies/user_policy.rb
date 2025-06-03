class UserPolicy < ApplicationPolicy
  prop :record, _Union(_Class(User), User), :positional, reader: :public

  def update_email? = true
end
