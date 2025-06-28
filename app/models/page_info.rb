class PageInfo < Literal::Data
  prop :title, String
  prop :flash, _Nilable(ActionDispatch::Flash::FlashHash)
end
