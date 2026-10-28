from django.urls import path

from . import views

app_name = "chat"
urlpatterns = [
    path("", views.ChatView.as_view(), name="room"),
    path("messages/", views.MessageListView.as_view(), name="messages"),
    path("send/", views.MessageCreateView.as_view(), name="send"),
]
