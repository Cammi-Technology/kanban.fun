class AuthorizationContext < Literal::Data
  prop :user, User, reader: :public
  prop :account_user, _Nilable(AccountUser)
end
