from django import template
from django.templatetags.static import static
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def icon(name):
    return format_html(
        '<svg class="icon" aria-hidden="true"><use href="{}?v=plain-1#{}"></use></svg>',
        static("icons.svg"),
        name,
    )


@register.simple_tag
def input_field(field):
    attrs = (
        {
            "class": "form-check-input"
            if field.field.widget.input_type == "checkbox"
            else "form-control"
        }
        if hasattr(field.field.widget, "input_type")
        else {"class": "form-control"}
    )
    if field.errors:
        attrs.update({"aria-invalid": "true", "aria-describedby": f"{field.auto_id}_errors"})
    elif field.help_text:
        attrs["aria-describedby"] = f"{field.auto_id}_help"
    return field.as_widget(attrs=attrs)
