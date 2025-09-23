from django import template

register = template.Library()

@register.filter
def lookup(queryset, field):
    return [getattr(item, field) for item in queryset]