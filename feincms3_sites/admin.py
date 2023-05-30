from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin import widgets
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _

from feincms3_sites.models import Site


class DefaultLanguageListFilter(admin.SimpleListFilter):
    """
    Simple list filter for the default_language property.
    """

    title = capfirst(_("default language"))
    parameter_name = "default_language"

    def lookups(self, request, model_admin):
        return [("", capfirst(_("no language")))] + list(settings.LANGUAGES)

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(default_language=self.value())
        else:
            return queryset.all()


class SiteForm(forms.ModelForm):
    default_language = Site._meta.get_field("default_language").formfield(
        choices=[("", "----------")] + list(settings.LANGUAGES),
        widget=widgets.AdminRadioSelect,
    )

    class Meta:
        model = Site
        fields = "__all__"  # noqa: DJ007


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
    list_filter = ["is_active", "host", DefaultLanguageListFilter]
