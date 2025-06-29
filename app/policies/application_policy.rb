# frozen_string_literal: true

class ApplicationPolicy
  extend Literal::Properties

  prop :authorization_context, AuthorizationContext, :positional, reader: :public
  prop :record, _Never, :positional, reader: :public

  def index?
    false
  end

  def show?
    false
  end

  def create?
    false
  end

  def new?
    create?
  end

  def update?
    false
  end

  def edit?
    update?
  end

  def destroy?
    false
  end

  class Scope
    extend Literal::Properties

    prop :authorization_context, AuthorizationContext, :positional, reader: :public
    prop :scope, _Never, :positional, reader: :private

    def resolve
      raise NoMethodError, "You must define #resolve in #{self.class}"
    end

    def user
      authorization_context.user
    end

    def account_user
      authorization_context.account_user
    end
  end

  private

  def user
    authorization_context.user
  end

  def account_user
    authorization_context.account_user
  end
end
