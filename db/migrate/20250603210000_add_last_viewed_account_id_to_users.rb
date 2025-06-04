class AddLastViewedAccountIdToUsers < ActiveRecord::Migration[8.0]
  def change
    add_reference :users, :last_viewed_account, foreign_key: { to_table: :accounts }
  end
end
