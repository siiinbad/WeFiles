from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .avatars import AVATAR_CHOICES

User = get_user_model()


class RegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "username", "display_name")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account already uses that email. Try signing in or resetting your password."
            )
        return email

    def clean_username(self):
        name = self.cleaned_data["username"]
        if User.objects.filter(username__iexact=name).exists():
            raise forms.ValidationError("That username is taken. Please choose another.")
        return name


class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
    )


class AvatarPicker(forms.RadioSelect):
    template_name = "accounts/widgets/avatar_picker.html"


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("avatar_icon", "username", "display_name")
        widgets = {"avatar_icon": AvatarPicker()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Older clients may still submit only the two original profile fields.
        self.fields["avatar_icon"].required = False
        self.fields["avatar_icon"].choices = AVATAR_CHOICES

    def clean_avatar_icon(self):
        return self.cleaned_data.get("avatar_icon") or self.instance.avatar_icon

    def clean_username(self):
        name = self.cleaned_data["username"]
        if User.objects.filter(username__iexact=name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("That username is taken. Please choose another.")
        return name


class DeleteAccountForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"})
    )
    confirm = forms.BooleanField(
        label="I understand that my account, uploaded files, and messages will be permanently deleted."
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("That password did not match. Please try again.")
        return password
