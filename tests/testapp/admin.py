from django.contrib import admin
from django.utils.text import capfirst
from django.utils.translation import ugettext_lazy as _

from content_editor.admin import ContentEditor
from feincms3 import plugins
from feincms3.admin import AncestorFilter, TreeAdmin

from . import models


@admin.register(models.Page)
class PageAdmin(ContentEditor, TreeAdmin):
    list_display = [
        "indented_title",
        "move_column",
        "is_active",
        "menu",
        "language_code",
        "template_key",
        "application",
    ]
    list_filter = ["is_active", "menu", AncestorFilter]
    list_editable = ["is_active"]
    prepopulated_fields = {"slug": ("title",)}
    radio_fields = {
        "menu": admin.HORIZONTAL,
        "language_code": admin.HORIZONTAL,
        "template_key": admin.HORIZONTAL,
        "application": admin.HORIZONTAL,
    }
    raw_id_fields = ["parent"]

    fieldsets = [
        (None, {"fields": ("is_active", "title", "parent")}),
        (
            capfirst(_("path")),
            {"fields": ("site", "slug", "static_path", "path"), "classes": ("tabbed",)},
        ),
        (
            capfirst(_("settings")),
            {
                "fields": ("menu", "language_code", "template_key", "application"),
                "classes": ("tabbed",),
            },
        ),
    ]

    inlines = [plugins.snippet.SnippetInline.create(model=models.Snippet)]
