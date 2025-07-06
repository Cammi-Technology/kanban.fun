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
end
