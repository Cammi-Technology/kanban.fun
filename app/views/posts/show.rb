# frozen_string_literal: true

class Views::Posts::Show < Views::Base
  prop :post, Post, reader: :private

  def view_template
    h1 { post.title }
    raw safe(post.content.to_s)
  end

  def page_title = post.title
end
