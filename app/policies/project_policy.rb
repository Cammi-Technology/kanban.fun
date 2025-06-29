class ProjectPolicy < ApplicationPolicy
  prop :record, _Union(_Class(Project), Project), :positional, reader: :public

  def index? = true

  class Scope < ApplicationPolicy::Scope
    prop :scope, _Class(Project), :positional, reader: :private

    def resolve
      scope.where(account: account_user.account).all
    end
  end
end
