# frozen_string_literal: true

class Views::Posts::Index < Views::Base
  prop :posts, ActiveRecord::Relation(Post), reader: :private

  def view_template
    h1 { "Posts::Index" }
    p { "Find me in app/views/posts/index.rb" }
  end

  def page_title = t(".title")
end
