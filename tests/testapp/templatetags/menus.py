from collections import defaultdict

from django import template
from django.db.models import Q
from django.utils.translation import get_language

from testapp.models import Page


register = template.Library()


@register.simple_tag
def menus():
    menus = defaultdict(list)
    pages = Page.objects.active().filter(Q(language_code=get_language()), ~Q(menu=""))
    for page in pages:
        menus[page.menu].append(page)
    return menus
