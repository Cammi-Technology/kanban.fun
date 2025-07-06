class PostsController < ApplicationController
  include Projects

  def index
    render Views::Posts::Index.new(
      posts: policy_scope(Current.project.posts)
    )
  end

  def new
    authorize (post = Current.project.posts.new), :new?

    render Views::Posts::New.new(
      post: post
    )
  end

  def create
    authorize (post = Current.project.posts.new(post_params)), :create?

    post.save!

    redirect_to [ Current.account, Current.project, post ], notice: t(".success")
  rescue ActiveRecord::RecordInvalid => e
    render Views::Posts::New.new(
      post: e.record
    ), status: :unprocessable_entity
  end

  def show
    authorize (post = Current.project.posts.find(params[:id])), :show?

    render Views::Posts::Show.new(
      post: post
    )
  end


  private

  def post_params
    params.expect(post: [ :title, :content, :category, :published ]).merge(
      author: Current.account_user
    )
  end
end
