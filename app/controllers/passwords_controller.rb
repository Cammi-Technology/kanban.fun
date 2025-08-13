class PasswordsController < ApplicationController
  before_action :set_user

  def edit
    authorize @user, :edit_password?
  end

  def update
    authorize @user, :update_password?

    if @user.update(user_params)
      redirect_to root_path, notice: "Your password has been changed"
    else
      render :edit, status: :unprocessable_content
    end
  end

  private
    def set_user
      @user = Current.user
    end

    def user_params
      params.permit(:password, :password_confirmation, :password_challenge).with_defaults(password_challenge: "")
    end
end
