from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin import widgets
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _

from .models import Site


class SiteForm(forms.ModelForm):
    default_language = Site._meta.get_field("default_language").formfield(
        choices=[("", "----------")] + list(settings.LANGUAGES),
        widget=widgets.AdminRadioSelect,
    )

    class Meta:
        model = Site
        fields = "__all__"


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {"fields": ("is_default", "host")}),
        (
            capfirst(_("advanced")),
            {
                "fields": ("is_managed_re", "host_re", "default_language"),
                "classes": ("collapse",),
            },
        ),
    ]
    form = SiteForm
    list_display = [
        "host",
        "is_active",
        "is_default",
        "is_managed_re",
        "host_re",
        "default_language",
    ]
    list_editable = ["is_active", "is_default"]
    ordering = ["-is_default", "host"]
