# frozen_string_literal: true

class ApplicationPolicy
  extend Literal::Properties

  prop :user, User, :positional, reader: :public
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

  private def account_user
    raise "Should be class AccountUser but received #{user.class_name}" unless user.is_a?(AccountUser)

    user
  end

  class Scope
    extend Literal::Properties

    prop :user, User, :positional, reader: :public
    prop :scope, _Never, :positional, reader: :private

    def resolve
      raise NoMethodError, "You must define #resolve in #{self.class}"
    end
  end
end
