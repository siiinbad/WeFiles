from django import forms


class MessageForm(forms.Form):
    content = forms.CharField(
        label="Message",
        max_length=2000,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Write to the crew…"}),
    )
