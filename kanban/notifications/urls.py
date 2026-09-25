from django.urls import path

from kanban.notifications import views

app_name = "notifications"

urlpatterns = [
    path("", views.index, name="index"),
    path("read-all/", views.read_all, name="read_all"),
    path("<int:notification_id>/open/", views.open_notification, name="open"),
    path("web-push/subscribe/", views.subscribe, name="subscribe"),
    path("web-push/unsubscribe/", views.unsubscribe, name="unsubscribe"),
]
