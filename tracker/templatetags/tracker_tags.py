from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def cat_icon(icon, color, size="text-xl"):
    """
    Render a category icon.
    - ASCII-only string → Tabler Icon class (e.g. "fork" → ti ti-fork)
    - Non-ASCII (emoji) → plain span
    """
    if icon and all(ord(c) < 128 for c in icon):
        return format_html(
            '<i class="ti ti-{} {}" style="color:{}"></i>',
            icon, size, color
        )
    return format_html('<span>{}</span>', icon or '📦')
