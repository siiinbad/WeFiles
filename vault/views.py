import csv
import logging
import uuid

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import FileResponse, Http404, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, FormView, ListView, View

from core.access import AdminMixin, ApprovedMixin, approved_required

from .forms import FileForm, FolderForm, UploadForm
from .models import File, Folder
from .selectors import breadcrumbs, file_query
from .services import (
    delete_file,
    delete_folder,
    process_deletions,
    save_folder,
    toggle_favorite,
    update_file,
    upload_file,
)

logger = logging.getLogger(__name__)


def resolve_folder(value):
    try:
        folder_id = uuid.UUID(str(value))
    except ValueError:
        raise Http404("That folder could not be found.") from None
    return get_object_or_404(Folder, pk=folder_id)


class FileListView(ApprovedMixin, ListView):
    template_name = "vault/list.html"
    context_object_name = "files"
    paginate_by = 25
    saved_only = False

    def get_queryset(self):
        self.folder = (
            get_object_or_404(Folder, pk=self.kwargs["pk"]) if "pk" in self.kwargs else None
        )
        queryset, self.filter_form = file_query(
            self.request.user, self.request.GET, self.folder, self.saved_only
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        folders = Folder.objects.filter(parent=self.folder).order_by("name", "pk")
        folder_page = Paginator(folders, 12).get_page(self.request.GET.get("folder_page"))
        context.update(
            folder=self.folder,
            breadcrumbs=breadcrumbs(self.folder),
            filter_form=self.filter_form,
            folders=folder_page if not self.saved_only and not self.request.GET.get("q") else [],
            folder_page=folder_page,
            saved_only=self.saved_only,
        )
        return context


class FileDetailView(ApprovedMixin, DetailView):
    template_name = "vault/detail.html"
    context_object_name = "file"

    def get_queryset(self):
        return File.objects.select_related("owner", "folder")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_saved"] = self.object.favorites.filter(user=self.request.user).exists()
        return context


class FileUploadView(ApprovedMixin, FormView):
    form_class = UploadForm
    template_name = "vault/form.html"
    extra_context = {
        "title": "Upload a file",
        "subtitle": "Give your crew something useful.",
        "submit_label": "Upload file",
        "upload": True,
    }

    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get("folder"):
            initial["folder"] = resolve_folder(self.request.GET["folder"])
        return initial

    def form_valid(self, form):
        try:
            file = upload_file(
                self.request.user,
                form.cleaned_data["file"],
                form.cleaned_data["folder"],
                form.cleaned_data["description"],
            )
        except (ValidationError, IntegrityError) as exc:
            form.add_error(
                None,
                " ".join(exc.messages)
                if isinstance(exc, ValidationError)
                else "The destination changed. Please try again.",
            )
            return self.form_invalid(form)
        except OSError:
            logger.exception("Private file upload failed")
            form.add_error(None, "The file could not be stored. Please try again shortly.")
            return self.form_invalid(form)
        messages.success(self.request, "Your file is ready for the crew.")
        return redirect("vault:detail", pk=file.pk)


class FolderCreateView(ApprovedMixin, FormView):
    form_class = FolderForm
    template_name = "vault/form.html"
    extra_context = {
        "title": "Create a folder",
        "subtitle": "A little structure goes a long way.",
        "submit_label": "Create folder",
    }

    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get("parent"):
            initial["parent"] = resolve_folder(self.request.GET["parent"])
        return initial

    def form_valid(self, form):
        try:
            folder = save_folder(self.request.user, form.save(commit=False))
        except (ValidationError, IntegrityError) as exc:
            form.add_error(
                None,
                " ".join(exc.messages)
                if isinstance(exc, ValidationError)
                else "A folder with this name already exists here.",
            )
            return self.form_invalid(form)
        messages.success(self.request, "Folder saved.")
        return redirect("vault:folder", pk=folder.pk)


class FolderUpdateView(AdminMixin, FolderCreateView):
    extra_context = {
        "title": "Edit folder",
        "subtitle": "Rename or move this folder and keep its contents together.",
        "submit_label": "Save changes",
    }

    def get_form_kwargs(self):
        return {
            **super().get_form_kwargs(),
            "instance": get_object_or_404(Folder, pk=self.kwargs["pk"]),
        }


class FileUpdateView(AdminMixin, FormView):
    form_class = FileForm
    template_name = "vault/form.html"
    extra_context = {
        "title": "Edit file details",
        "subtitle": "Update the name, description, or location.",
        "submit_label": "Save changes",
    }

    def get_form_kwargs(self):
        return {
            **super().get_form_kwargs(),
            "instance": get_object_or_404(File, pk=self.kwargs["pk"]),
        }

    def form_valid(self, form):
        try:
            file = update_file(self.request.user, form.save(commit=False))
        except (ValidationError, IntegrityError) as exc:
            form.add_error(
                None,
                " ".join(exc.messages)
                if isinstance(exc, ValidationError)
                else "That destination changed. Please try again.",
            )
            return self.form_invalid(form)
        messages.success(self.request, "File details updated.")
        return redirect("vault:detail", pk=file.pk)


class DeleteView(AdminMixin, View):
    model = File

    def get(self, request, pk):
        return render(
            request, "vault/confirm_delete.html", {"object": get_object_or_404(self.model, pk=pk)}
        )

    def post(self, request, pk):
        obj = get_object_or_404(self.model, pk=pk)
        if request.POST.get("confirm") != "yes":
            messages.error(request, "Please confirm the deletion.")
            return self.get(request, pk)
        try:
            (delete_file if self.model is File else delete_folder)(request.user, obj)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
            return self.get(request, pk)
        process_deletions(limit=10)
        messages.success(request, "Deleted successfully.")
        return redirect("vault:list")


@approved_required
def download(request, pk):
    file = get_object_or_404(File, pk=pk)
    try:
        response = FileResponse(
            file.blob.open("rb"),
            as_attachment=True,
            filename=file.name,
            content_type="application/octet-stream",
        )
    except (FileNotFoundError, OSError):
        logger.warning("A private download object was unavailable")
        raise Http404("This file is unavailable. Please contact an administrator.") from None
    response["X-Content-Type-Options"] = "nosniff"
    return response


@approved_required
@require_POST
def favorite(request, pk):
    file = get_object_or_404(File, pk=pk)
    saved = toggle_favorite(request.user, file)
    if request.headers.get("HX-Request"):
        return render(request, "vault/favorite.html", {"file": file, "is_saved": saved})
    messages.success(request, "File saved." if saved else "File removed from saved.")
    return redirect("vault:detail", pk=pk)


def csv_safe(value):
    value = str(value or "")
    return (
        "'" + value
        if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n"))
        else value
    )


class Echo:
    def write(self, value):
        return value


@approved_required
def export_csv(request):
    folder = None
    if request.GET.get("folder"):
        folder = resolve_folder(request.GET["folder"])
    files, _ = file_query(request.user, request.GET, folder, request.GET.get("saved") == "on")
    writer = csv.writer(Echo())

    def rows():
        yield writer.writerow(
            ["Name", "Description", "Folder", "Size (bytes)", "Uploaded by", "Uploaded at"]
        )
        for file in files.iterator(chunk_size=500):
            yield writer.writerow(
                [
                    csv_safe(v)
                    for v in (
                        file.name,
                        file.description,
                        file.folder.name if file.folder else "Vault root",
                        file.size_bytes,
                        file.owner.username,
                        file.created_at.isoformat(),
                    )
                ]
            )

    response = StreamingHttpResponse(rows(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="wefiles-inventory.csv"'
    return response
