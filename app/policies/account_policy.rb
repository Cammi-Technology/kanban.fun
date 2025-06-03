class AccountPolicy < ApplicationPolicy
  prop :record, Account, :positional, reader: :public

  def show?
    user == record.owner
  end

  class Scope < ApplicationPolicy::Scope
    prop :scope, _Class(Account), :positional, reader: :private

    def resolve
      scope.where(owner: user).all
    end
  end
end
