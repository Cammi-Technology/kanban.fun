class RenameCommentableToRecordInComments < ActiveRecord::Migration[8.0]
  def change
    rename_column :comments, :commentable_type, :record_type
    rename_column :comments, :commentable_id, :record_id
    rename_index :comments, :index_comments_on_commentable, :index_comments_on_record
  end
end
