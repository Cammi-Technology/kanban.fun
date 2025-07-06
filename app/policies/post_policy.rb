class PostPolicy < ApplicationPolicy
  prop :user, AccountUser, :positional, reader: :public
  prop :record, _Union(_Class(Post), Post), :positional, reader: :public

  def index? = true

  def new?
    user.account == record.project.account
  end

  def create? = new?

  class Scope < ApplicationPolicy::Scope
    prop :user, AccountUser, :positional, reader: :public
    prop :scope, _Union(_Class(Post), ActiveRecord::Relation(Post)), :positional, reader: :private

    def resolve
      scope.where(project: user.account.projects).all
    end
  end
end
