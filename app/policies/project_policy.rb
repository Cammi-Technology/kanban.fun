class ProjectPolicy < ApplicationPolicy
  prop :record, _Union(_Class(Project), Project), :positional, reader: :public
  prop :authorization_context, _Constraint(AuthorizationContext, account_user: AccountUser), :positional, reader: :public

  def index? = true

  def new?
    account_user.account == record.account
  end

  def create? = new?
  def show? = new?

  class Scope < ApplicationPolicy::Scope
    prop :scope, _Class(Project), :positional, reader: :private
    prop :authorization_context, _Constraint(AuthorizationContext, account_user: AccountUser), :positional, reader: :public

    def resolve
      scope.where(account: account_user.account).all
    end
  end
end
