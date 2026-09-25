from django.apps import AppConfig


class IdentityConfig(AppConfig):
    name = "kanban.identity"
    label = "identity"
    verbose_name = "Identity"

    def ready(self) -> None:
        from django.contrib.auth.signals import user_logged_in

        from kanban.identity.services import on_user_logged_in

        user_logged_in.connect(on_user_logged_in, dispatch_uid="device-session")
