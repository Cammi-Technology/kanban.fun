# frozen_string_literal: true

class Views::Posts::Index < Views::Base
  prop :posts, ActiveRecord::Relation(Post), reader: :private

  def view_template
    h1 { t(".title") }
    p { t(".description") }

    if posts.any?
      a(href: new_account_project_post_path(posts.first.project.account, posts.first.project)) do
        t(".new")
      end

      ul do
        posts.each do |post|
          li do
            a(href: account_project_post_path(post.project.account, post.project, post)) do
              post.title
            end
          end
        end
      end
    else
      p { t(".no_posts") }
      a(href: new_account_project_post_path(Current.account, Current.project)) do
        t(".new")
      end
    end
  end

  def page_title = t(".title")
end
