# frozen_string_literal: true

class Views::Accounts::New < Views::Base
  include Phlex::Rails::Helpers::FormWith

  prop :account, Account, reader: :private, default: -> { Account.new }

  def view_template
    p { t(".description") }
    show_form
  end

  private

  def page_title = t(".title")

  def show_form
    form_with model: account do |form|
      if form.object.errors.any?
        form.object.errors.full_messages.each do |message|
          plain message
        end
      end

      FormField do
        FormLabel(for: "account_name") { t("activerecord.attributes.account.name") }
        FormInput(
          name: "account[name]",
          id: "account_name",
          required: true,
          placeholder: t("placeholders.account.name"),
          value: form.object.name
        )
      end

      FormField do
        Button(type: "submit") { "Create Account" }
      end
    end
  end
end
