class UserPolicy < ApplicationPolicy
  prop :record, _Union(_Class(User), User), :positional, reader: :public

  # home controller
  def visit_home? = true

  # identity controller actions
  def create_email_verification? = true
  def edit_password? = true
  def update_password? = true
  def edit_email? = true
  def update_email? = true
end
