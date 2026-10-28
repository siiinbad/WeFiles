from django import forms
from django.conf import settings

from .models import File, Folder, validate_name


class UploadForm(forms.Form):
    file = forms.FileField(
        help_text="One file at a time, up to 50 MiB. Files stay private to approved members."
    )
    folder = forms.ModelChoiceField(
        queryset=Folder.objects.all(), required=False, empty_label="Vault root"
    )
    description = forms.CharField(
        max_length=1000, required=False, widget=forms.Textarea(attrs={"rows": 3})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[
            "file"
        ].help_text = f"One file at a time, up to {settings.MAX_UPLOAD_BYTES // 1024 // 1024} MiB. Private to approved members."
        self.fields["file"].widget.attrs["data-max-bytes"] = settings.MAX_UPLOAD_BYTES

    def clean_file(self):
        upload = self.cleaned_data["file"]
        validate_name(upload.name)
        if len(upload.name) > 255:
            raise forms.ValidationError("Use a filename of 255 characters or fewer.")
        if upload.size > settings.MAX_UPLOAD_BYTES:
            raise forms.ValidationError(
                f"Choose a file smaller than {settings.MAX_UPLOAD_BYTES // 1024 // 1024} MiB."
            )
        if upload.size == 0:
            raise forms.ValidationError("That file is empty. Choose a file with some content.")
        return upload


class FolderForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ["name", "parent"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].empty_label = "Vault root"
        if self.instance.pk:
            self.fields["parent"].queryset = Folder.objects.exclude(pk=self.instance.pk)


class FileForm(forms.ModelForm):
    class Meta:
        model = File
        fields = ["name", "description", "folder"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class VaultFilterForm(forms.Form):
    q = forms.CharField(max_length=100, required=False, label="Search files")
    kind = forms.ChoiceField(
        required=False,
        choices=[
            ("", "All types"),
            ("pdf", "PDF"),
            ("image", "Images"),
            ("sheet", "Spreadsheets"),
            ("document", "Other files"),
        ],
    )
    sort = forms.ChoiceField(
        required=False,
        choices=[
            ("", "Newest first"),
            ("oldest", "Oldest first"),
            ("name", "Name A–Z"),
            ("size", "Largest first"),
        ],
    )
    owner = forms.UUIDField(required=False, label="Uploader")
    saved = forms.BooleanField(required=False)
