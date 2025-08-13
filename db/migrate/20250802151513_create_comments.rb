class CreateComments < ActiveRecord::Migration[8.0]
  def change
    create_table :comments do |t|
      t.references :author, null: false, foreign_key: { to_table: :account_users }
      t.references :commentable, null: false, polymorphic: true

      t.timestamps
    end
  end
end
