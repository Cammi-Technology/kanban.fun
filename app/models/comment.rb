class Comment < ApplicationRecord
  belongs_to :author, class_name: "AccountUser"
  belongs_to :commentable, polymorphic: true

  has_rich_text :content

  validates :author, presence: true
  validates :content, presence: true
end
