from django.apps import AppConfig
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _


class SitesAppConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"

    name = "feincms3_sites"
    verbose_name = capfirst(_("sites"))
