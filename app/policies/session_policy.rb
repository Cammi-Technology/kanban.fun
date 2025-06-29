class SessionPolicy < ApplicationPolicy
  prop :record, _Union(_Class(Session), Session), :positional, reader: :public

  def index? = true
  def new? = true

  def destroy?
    record.user == user
  end

  class Scope < ApplicationPolicy::Scope
    prop :scope, ActiveRecord::Relation(Session), :positional, reader: :private

    def resolve
      scope.all.where(user: user)
    end
  end
end
