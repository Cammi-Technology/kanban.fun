class AccountUserPolicy < ApplicationPolicy
  class Scope < ApplicationPolicy::Scope
    prop :user, AccountUser, :positional, reader: :public
    prop :scope, _Union(_Class(AccountUser), ActiveRecord::Relation(AccountUser)), :positional, reader: :private

    def resolve
      scope.where(account: user.account).all
    end
  end
end
