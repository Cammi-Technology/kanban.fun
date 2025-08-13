class CommentPolicy < ApplicationPolicy
  prop :user, AccountUser, :positional, reader: :public
  prop :record, _Union(_Class(Comment), Comment), :positional, reader: :public

  def create? = same_account?
  def destroy? = same_account?

  private

  def same_account?
    commentable = record.commentable
    commentable.respond_to?(:project) && commentable.project.account == user.account
  end
end
