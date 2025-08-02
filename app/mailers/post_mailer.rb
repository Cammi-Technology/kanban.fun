class PostMailer < ApplicationMailer
  # Subject can be set in your I18n file at config/locales/en.yml
  # with the following lookup:
  #
  #   en.post_mailer.new_post.subject
  #
  def new_post
    @user = params[:recipient]

    mail to: @user.email
  end
end
