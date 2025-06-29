class InvitationsController < ApplicationController
  skip_after_action :verify_pundit_authorization
  def new
    @user = User.new
  end

  def create
    @user = User.create_with(user_params).find_or_initialize_by(email: params[:email])

    if @user.save
      send_invitation_instructions
      redirect_to new_invitation_path, notice: t("invitations.create.success", email: @user.email)
    else
      flash.now[:alert] = t("invitations.create.error")
      render :new, status: :unprocessable_entity
    end
  end

  private
    def user_params
      params.permit(:email).merge(password: SecureRandom.base58, verified: true)
    end

    def send_invitation_instructions
      UserMailer.with(user: @user).invitation_instructions.deliver_later
    end
end
