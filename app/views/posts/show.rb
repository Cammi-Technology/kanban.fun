# frozen_string_literal: true

class Views::Posts::Show < Views::Base
  prop :post, Post, reader: :private

  def view_template
    h1 { post.title }
    raw safe(post.content.to_s)

    div do
      h2 { "Comments" }

      post.comments.each do |comment|
        div do
          raw safe(comment.content.to_s)
        end
      end

      CommentForm(record: post)
    end
  end

  def page_title = post.title
end
