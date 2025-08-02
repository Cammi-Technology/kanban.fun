class Project < ApplicationRecord
  belongs_to :account

  has_many :posts, dependent: :destroy

  validates :name, presence: true
end
