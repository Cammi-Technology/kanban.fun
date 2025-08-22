# frozen_string_literal: true

class Views::Posts::Show < Views::Base
  prop :post, Post, reader: :private

  def view_template
    h1 { post.title }

    if policy(post).edit?
      div do
        a(href: edit_account_project_post_path(Current.account, Current.project, post)) { "Edit" }
      end
    end

    div(data_controller: "syntax-highlight") do
      raw safe(post.content.to_s)
    end

    div do
      h2 { "Comments" }

      post.comments.each do |comment|
        div(data_controller: "syntax-highlight") do
          raw safe(comment.content.to_s)
        end
      end

      CommentForm(record: post)
    end
  end

  def page_title = post.title
end
