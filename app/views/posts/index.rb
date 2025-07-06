# frozen_string_literal: true

class Views::Posts::Index < Views::Base
  prop :posts, ActiveRecord::Relation(Post), reader: :private

  def view_template
    h1 { t(".title") }
    p { t(".description") }

    posts.each do |post|
      a(href: account_project_post_path(post.project.account, post.project, post)) do
        post.title
      end
    end
  end

  def page_title = t(".title")
end
