class AccountsApplicationController < ApplicationController
  def pundit_user
    Current.account_user
  end
end
