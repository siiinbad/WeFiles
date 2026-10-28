from django.urls import path

from . import views
from .models import Folder

app_name = "vault"
urlpatterns = [
    path("", views.FileListView.as_view(), name="list"),
    path("saved/", views.FileListView.as_view(saved_only=True), name="saved"),
    path("export.csv", views.export_csv, name="export"),
    path("upload/", views.FileUploadView.as_view(), name="upload"),
    path("folders/new/", views.FolderCreateView.as_view(), name="folder_create"),
    path("folders/<uuid:pk>/", views.FileListView.as_view(), name="folder"),
    path("folders/<uuid:pk>/edit/", views.FolderUpdateView.as_view(), name="folder_edit"),
    path("folders/<uuid:pk>/delete/", views.DeleteView.as_view(model=Folder), name="folder_delete"),
    path("files/<uuid:pk>/", views.FileDetailView.as_view(), name="detail"),
    path("files/<uuid:pk>/download/", views.download, name="download"),
    path("files/<uuid:pk>/edit/", views.FileUpdateView.as_view(), name="edit"),
    path("files/<uuid:pk>/delete/", views.DeleteView.as_view(), name="delete"),
    path("files/<uuid:pk>/save/", views.favorite, name="favorite"),
]
