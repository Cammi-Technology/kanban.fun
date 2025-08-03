Rails.application.routes.draw do
  resources :web_push_subscriptions, param: :endpoint, only: [ :create, :destroy ]
  namespace :authentications do
    resources :events, only: :index
  end
  namespace :two_factor_authentication do
    namespace :challenge do
      resource :totp,           only: [ :new, :create ]
      resource :recovery_codes, only: [ :new, :create ]
    end
    namespace :profile do
      resource  :totp,           only: [ :new, :create, :update ]
      resources :recovery_codes, only: [ :index, :create ]
    end
  end
  get  "/auth/failure",            to: "sessions/omniauth#failure"
  get  "/auth/:provider/callback", to: "sessions/omniauth#create"
  post "/auth/:provider/callback", to: "sessions/omniauth#create"
  resource :invitation, only: [ :new, :create ]
  namespace :sessions do
    resource :passwordless, only: [ :new, :edit, :create ]
    resource :sudo, only: [ :new, :create ]
  end
  get  "sign_in", to: "sessions#new"
  post "sign_in", to: "sessions#create"
  get  "sign_up", to: "registrations#new"
  post "sign_up", to: "registrations#create"

  resources :accounts, only: [ :new, :index, :create ] do
    resource :dashboard, only: [ :show ]
    resources :projects, only: [ :index, :new, :create, :show ] do
      resources :posts, only: [ :index, :new, :create, :show ]
    end
  end

  resources :sessions, only: [ :index, :show, :destroy ]
  resource  :password, only: [ :edit, :update ]

  namespace :identity do
    resource :email,              only: [ :edit, :update ]
    resource :email_verification, only: [ :show, :create ]
    resource :password_reset,     only: [ :new, :edit, :create, :update ]
  end
  root "home#index"
  # Define your application routes per the DSL in https://guides.rubyonrails.org/routing.html

  # Reveal health status on /up that returns 200 if the app boots with no exceptions, otherwise 500.
  # Can be used by load balancers and uptime monitors to verify that the app is live.
  get "up" => "rails/health#show", as: :rails_health_check

  # Render dynamic PWA files from app/views/pwa/* (remember to link manifest in application.html.erb)
  # get "manifest" => "rails/pwa#manifest", as: :pwa_manifest
  # get "service-worker" => "rails/pwa#service_worker", as: :pwa_service_worker

  # Defines the root path route ("/")
  # root "posts#index"
end
