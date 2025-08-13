module Commentable
  extend ActiveSupport::Concern

  included do
    has_many :comments, as: :record, dependent: :destroy
  end
end
