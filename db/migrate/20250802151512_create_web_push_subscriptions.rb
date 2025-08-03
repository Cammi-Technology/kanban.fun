class CreateWebPushSubscriptions < ActiveRecord::Migration[8.0]
  def change
    create_table :noticed_web_push_subscriptions do |t|
      t.references :user, null: false, foreign_key: true
      t.string :endpoint, null: false
      t.string :p256dh, null: false
      t.string :auth, null: false
      t.timestamps
    end

    add_index :noticed_web_push_subscriptions, :endpoint, unique: true
  end
end
