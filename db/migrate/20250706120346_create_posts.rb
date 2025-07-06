class CreatePosts < ActiveRecord::Migration[8.0]
  def change
    create_table :posts do |t|
      t.string :title, null: false
      t.string :category
      t.belongs_to :author, null: false, foreign_key: { to_table: :account_users }
      t.belongs_to :project, null: false, foreign_key: true
      t.boolean :published, default: false, null: false

      t.timestamps
    end
  end
end
