"""Account presentation helpers shared through the accounts template library."""

from django import template
from django.templatetags.static import static
from django.utils.html import format_html

from accounts.avatars import PORTRAIT_PADDING, PORTRAIT_REGIONS, PORTRAIT_SIZE, PORTRAIT_SOURCE
from core.templatetags.ui import icon

register = template.Library()


@register.simple_tag
def avatar_art(name):
    """Contain a complete source tile inside an inset frame, without cover cropping.

    The inner SVG clips exactly at the original cell boundary, preventing an
    adjacent portrait from bleeding into the outer frame's safe white space.
    Its matching viewport/viewBox aspect ratios preserve every source pixel.
    """
    if name not in PORTRAIT_REGIONS:
        return icon(name)
    x, y, width, height = PORTRAIT_REGIONS[name]
    padding = PORTRAIT_PADDING
    return format_html(
        '<svg class="avatar-art portrait-art" data-portrait="{}" '
        'viewBox="{} {} {} {}" preserveAspectRatio="xMidYMid meet" aria-hidden="true">'
        '<rect x="{}" y="{}" width="{}" height="{}" fill="#fff"/>'
        '<svg x="{}" y="{}" width="{}" height="{}" viewBox="{} {} {} {}" '
        'preserveAspectRatio="none" overflow="hidden">'
        '<image href="{}" x="0" y="0" width="{}" height="{}"/>'
        "</svg></svg>",
        name,
        x - padding,
        y - padding,
        width + 2 * padding,
        height + 2 * padding,
        x - padding,
        y - padding,
        width + 2 * padding,
        height + 2 * padding,
        x,
        y,
        width,
        height,
        x,
        y,
        width,
        height,
        static(PORTRAIT_SOURCE),
        *PORTRAIT_SIZE,
    )
