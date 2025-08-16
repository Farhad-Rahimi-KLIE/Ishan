from django import template
import json

register = template.Library()

@register.filter
def json_parse(value):
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}  # Return empty dict on failure