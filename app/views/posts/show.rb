# frozen_string_literal: true

class Views::Posts::Show < Views::Base
  prop :post, Post, reader: :private

  def view_template
    ContentShell(width: :wide, class: "posts-show") do
      div(class: "posts-show__topbar") do
        p(class: "posts-show__breadcrumb") do
          plain Current.project.name
          plain "  <  "
          plain t("views.posts.index.title")
        end

        if policy(post).edit?
          a(
            href: edit_account_project_post_path(Current.account, Current.project, post),
            class: "posts-show__edit"
          ) { "Edit" }
        end
      end

      article class: "posts-show__panel surface-panel" do
        header(class: "posts-show__header") do
          h1(class: "posts-show__title") { post.title }
          p(class: "posts-show__meta") do
            plain post.author.name
            plain " • "
            plain formatted_date(post)
          end
        end

        div(
          class: "posts-show__content trix-content",
          data: { controller: "syntax-highlight" }
        ) do
          raw safe(post.content.to_s)
        end

        section(class: "posts-show__comments") do
          h2(class: "posts-show__comments-title") { "Comments" }

          if post.comments.any?
            ul(class: "posts-show__comments-list") do
              post.comments.each do |comment|
                li(class: "posts-show__comment") do
                  Avatar(
                    name: comment.author.name,
                    size: :md,
                    class: "posts-show__comment-avatar"
                  )

                  div(class: "posts-show__comment-body") do
                    p(class: "posts-show__comment-meta") do
                      plain comment.author.name
                      plain " • "
                      plain formatted_date(comment)
                    end

                    div(
                      class: "posts-show__comment-content trix-content",
                      data: { controller: "syntax-highlight" }
                    ) do
                      raw safe(comment.content.to_s)
                    end
                  end
                end
              end
            end
          end

          div(class: "posts-show__comment-form-wrap") do
            CommentForm(record: post, class: "posts-show__comment-form")
          end
        end
      end
    end
  end

  private

  def formatted_date(record)
    record.created_at.strftime("%b %-d")
  end

  def page_title = post.title
end
