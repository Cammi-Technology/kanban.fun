# frozen_string_literal: true

class Views::Posts::Index < Views::Base
  include PhlexIcons

  prop :posts, ActiveRecord::Relation(Post), reader: :private

  def view_template
    ContentShell(width: :wide, class: "posts-index") do
      div(class: "posts-index__topbar") do
        p(class: "posts-index__project-name") { Current.project.name }
      end

      div(class: "posts-index__panel surface-panel") do
        div(class: "posts-index__header") do
          h1(class: "posts-index__title") { t(".title") }
          p(class: "posts-index__description") { t(".description") }
        end

        div(class: "posts-index__actions") do
          a(href: new_post_path, class: "posts-index__new-post primary-button") do
            span(
              class: "posts-index__new-post-icon",
              aria: { hidden: "true" }
            ) do
              Icon("bootstrap/plus")
            end
            span { t(".new") }
          end
        end

        if posts.any?
          ul(class: "posts-index__list") do
            posts.each do |post|
              post_row(post)
            end
          end
        else
          div(class: "posts-index__empty") do
            p(class: "posts-index__empty-copy") { t(".no_posts") }
          end
        end
      end
    end
  end

  private

  def page_title = t(".title")

  def new_post_path
    new_account_project_post_path(Current.account, Current.project)
  end

  def post_row(post)
    li(class: "posts-index__item") do
      a(
        href: account_project_post_path(post.project.account, post.project, post),
        class: "posts-index__link"
      ) do
        Avatar(name: post.author.name, size: :lg, class: "posts-index__avatar")

        div(class: "posts-index__body") do
          h2(class: "posts-index__post-title") { post.title }

          p(class: "posts-index__meta") do
            plain post.author.name
            plain " • "
            plain formatted_date(post)
          end

          p(class: "posts-index__excerpt") { excerpt(post) }
        end

        if post.comments.any?
          span(class: "posts-index__count") { post.comments.size }
        end
      end
    end
  end

  def excerpt(post)
    content = post.content.to_plain_text.squish

    return content if content.length <= 180

    "#{content[0...177]}..."
  end

  def formatted_date(post)
    post.created_at.strftime("%b %-d")
  end
end
