class AccountPolicy < ApplicationPolicy
  prop :user, _Union(User, AccountUser), :positional, reader: :public
  prop :record, _Union(_Class(Account), Account), :positional, reader: :public

  def new? = true
  def create? = new?

  # controller actions
  def visit_dashboard?
    record.account_users.include?(account_user)
  end

  class Scope < ApplicationPolicy::Scope
    prop :user, _Union(User, AccountUser), :positional, reader: :public
    prop :scope, _Class(Account), :positional, reader: :private

    def resolve
      scope.where(owner: user).all
    end
  end
end
