# viewer/templatetags/viewer_extras.py
from django import template
import os  # Needed for basename()
register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, "")

@register.filter
def basename(value):
    return os.path.basename(value)