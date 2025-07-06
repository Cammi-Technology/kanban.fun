class Post < ApplicationRecord
  belongs_to :author, class_name: "AccountUser", foreign_key: "author_id"
  belongs_to :project

  validates :author, presence: true
  validates :title, presence: true
  validates :project, presence: true
  validates :published, presence: true
end
