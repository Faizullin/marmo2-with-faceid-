from django import template

register = template.Library()


@register.filter(name='length_is')
def split(value, key):
    return len(value) == key
