class AccountPolicy < ApplicationPolicy
  prop :record, _Union(_Class(Account), Account), :positional, reader: :public

  def new? = true
  def create? = new?

  # controller actions
  def visit_dashboard?
    record.users.include?(user)
  end

  class Scope < ApplicationPolicy::Scope
    prop :scope, _Class(Account), :positional, reader: :private

    def resolve
      scope.where(owner: user).all
    end
  end
end
