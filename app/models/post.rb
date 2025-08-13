class Post < ApplicationRecord
  include Commentable

  belongs_to :author, class_name: "AccountUser", foreign_key: "author_id"
  belongs_to :project

  validates :author, presence: true
  validates :title, presence: true
  validates :project, presence: true
  validates :published, presence: true

  has_rich_text :content

  after_create :notify_new_post

  delegate :account, to: :project

  private

  def notify_new_post
    NewPostNotifier.with(record: self).deliver(account.users)
  end
end
