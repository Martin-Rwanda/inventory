from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def percentage(quantity, minimum):
    """Calculate percentage of stock level"""
    if minimum == 0:
        return 100
    return min(int((quantity / minimum) * 100), 100)

@register.filter
def stock_level_color(percentage):
    """Return color class based on stock percentage"""
    if percentage < 25:
        return 'danger'
    elif percentage < 50:
        return 'warning'
    elif percentage < 75:
        return 'info'
    else:
        return 'success'