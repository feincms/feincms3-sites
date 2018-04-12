from django.contrib import admin

from .models import Site


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('host', 'is_default', 'host_re')
    ordering = ('-is_default',)
