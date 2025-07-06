class PostsController < ApplicationController
  include Projects

  def index
    render Views::Posts::Index.new(
      posts: policy_scope(Current.project.posts)
    )
  end
end
