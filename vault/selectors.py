from django.db.models import Exists, OuterRef, Q
from django.db.models.functions import Lower

from .forms import VaultFilterForm
from .models import Favorite, File


def file_query(user, params, folder=None, saved_only=False):
    """One allowlisted query powers HTML browsing, saved files, and CSV export."""
    form = VaultFilterForm(params)
    form.is_valid()
    data = form.cleaned_data
    files = File.objects.select_related("owner", "folder").annotate(
        is_saved=Exists(Favorite.objects.filter(user=user, file=OuterRef("pk")))
    )
    query = data.get("q", "")
    if query:
        files = files.filter(Q(name__icontains=query) | Q(description__icontains=query))
        if folder:
            files = files.filter(folder=folder)
    else:
        files = files.filter(folder=folder)
    if saved_only or data.get("saved"):
        # Saved browsing covers the entire vault, unless a folder is explicit.
        if not query and folder is None:
            files = File.objects.select_related("owner", "folder").annotate(
                is_saved=Exists(Favorite.objects.filter(user=user, file=OuterRef("pk")))
            )
        files = files.filter(is_saved=True)
    if data.get("owner"):
        files = files.filter(owner_id=data["owner"])
    kind = data.get("kind")
    pdf = Q(name__iendswith=".pdf")
    image = Q(content_type__startswith="image/")
    sheet = Q(name__iendswith=".csv") | Q(name__iendswith=".xls") | Q(name__iendswith=".xlsx")
    if kind == "pdf":
        files = files.filter(pdf)
    elif kind == "image":
        files = files.filter(image)
    elif kind == "sheet":
        files = files.filter(sheet)
    elif kind == "document":
        files = files.exclude(pdf | image | sheet)
    orders = {
        "oldest": ["created_at", "pk"],
        "name": [Lower("name"), "pk"],
        "size": ["-size_bytes", "pk"],
    }
    return files.order_by(*orders.get(data.get("sort"), ["-created_at", "-pk"])), form


def breadcrumbs(folder):
    parts, seen = [], set()
    while folder and folder.pk not in seen:
        seen.add(folder.pk)
        parts.append(folder)
        folder = folder.parent
    return list(reversed(parts))
