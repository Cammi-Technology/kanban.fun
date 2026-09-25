from django.apps import AppConfig


class CableConfig(AppConfig):
    name = "kanban.cable"
    label = "cable"
    verbose_name = "Cable"
