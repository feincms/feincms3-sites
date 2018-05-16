from django.apps import AppConfig
from django.utils.text import capfirst
from django.utils.translation import ugettext_lazy as _


class SitesAppConfig(AppConfig):
    name = "feincms3_sites"
    verbose_name = capfirst(_("sites"))
