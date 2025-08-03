# This file should ensure the existence of records required to run the application in every environment (production,
# development, test). The code here should be idempotent so that it can be executed at any point in every environment.
# The data can then be loaded with the bin/rails db:seed command (or created alongside the database with db:setup).
#
# Example:
#
#   ["Action", "Comedy", "Drama", "Horror"].each do |genre_name|
#     MovieGenre.find_or_create_by!(name: genre_name)
#   end

User.create!(
  email: "test@test.com",
  password_digest: BCrypt::Password.create("1234567890"),
  otp_secret: ROTP::Base32.random,
  first_name: "Test",
  last_name: "User"
)

account_owner = User.create!(
  email: "account_owner@test.com",
  password_digest: BCrypt::Password.create("1234567890"),
  first_name: "Account",
  last_name: "Owner",
  otp_secret: ROTP::Base32.random
)

account_user = User.create!(
  email: "account_user@test.com",
  password_digest: BCrypt::Password.create("1234567890"),
  first_name: "Account",
  last_name: "User",
  otp_secret: ROTP::Base32.random
)

account = Account.create!(
  owner: account_owner,
  name: "Account Inc."
)

account_user_owner = AccountUser.create!(
  user: account_owner,
  account: account
)

AccountUser.create!(
  user: account_user,
  account: account
)

project = Project.create!(
  account: account,
  name: "My very good project"
)

Post.create!(
  project: project,
  title: "Welcome to the project",
  content: "<p>Welcome</p>",
  author: account_user_owner,
  published: true
)
