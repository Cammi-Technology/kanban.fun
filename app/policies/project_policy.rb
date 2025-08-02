class ProjectPolicy < ApplicationPolicy
  prop :user, AccountUser, :positional, reader: :public
  prop :record, _Union(_Class(Project), Project), :positional, reader: :public

  def index? = true

  def new?
    user.account == record.account
  end

  def set_current_project? = new?
  def create? = new?
  def show? = new?

  class Scope < ApplicationPolicy::Scope
    prop :user, AccountUser, :positional, reader: :public
    prop :scope, _Class(Project), :positional, reader: :private

    def resolve
      scope.where(account: user.account).all
    end
  end
end
