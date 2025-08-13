class CommentsController < ApplicationController
  include Projects

  def create
    post = Current.project.posts.find(params[:post_id])
    authorize (comment = post.comments.new(comment_params.merge(author: Current.account_user))), :create?

    comment.save!

    redirect_to [ Current.account, Current.project, post ], notice: t(".success")
  rescue ActiveRecord::RecordInvalid
    render Views::Posts::Show.new(post: post), status: :unprocessable_content
  end

  def destroy
    post = Current.project.posts.find(params[:post_id])
    authorize (comment = post.comments.find(params[:id])), :destroy?

    comment.destroy!

    redirect_to [ Current.account, Current.project, post ], notice: t(".success")
  end

  private

  def comment_params
    params.expect(comment: [ :content ])
  end
end
