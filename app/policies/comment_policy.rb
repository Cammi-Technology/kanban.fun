class CommentPolicy < ApplicationPolicy
  prop :user, AccountUser, :positional, reader: :public
  prop :record, Comment, :positional, reader: :public

  def create? = same_account?
  def destroy? = same_account?

  class Scope < ApplicationPolicy::Scope
    prop :user, AccountUser, :positional, reader: :public
    prop :scope, _Union(_Class(Comment), ActiveRecord::Relation(Comment)), :positional, reader: :private

    def resolve
      scope.where(commentable: Post.where(project: user.account.projects))
    end
  end

  private

  def same_account?
    record.commentable.project.account == user.account
  end
end
