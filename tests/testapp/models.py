from content_editor.models import Region, create_plugin_base
from django.db import models
from django.utils.translation import gettext_lazy as _
from feincms3 import plugins
from feincms3.applications import (
    ApplicationType,
    PageTypeMixin,
    TemplateType,
    reverse_app,
)
from feincms3.mixins import LanguageMixin, MenuMixin, RedirectMixin

from feincms3_sites.models import AbstractPage, AbstractSite


class CustomSite(AbstractSite):
    title = models.CharField(max_length=100, blank=True)


class Page(AbstractPage, PageTypeMixin, MenuMixin, LanguageMixin, RedirectMixin):
    # MenuMixin
    MENUS = [("main", _("main")), ("footer", _("footer"))]

    # PageTypeMixin. We have two templates and four apps.
    TYPES = [
        TemplateType(
            key="standard",
            title=_("standard"),
            template_name="pages/standard.html",
            regions=(Region(key="main", title=_("Main")),),
        ),
        TemplateType(
            key="with-sidebar",
            title=_("with sidebar"),
            template_name="pages/with-sidebar.html",
            regions=(
                Region(key="main", title=_("Main")),
                Region(key="sidebar", title=_("Sidebar")),
            ),
        ),
        ApplicationType(
            key="publications",
            title=_("publications"),
            urlconf="testapp.articles_urls",
        ),
        ApplicationType(
            key="blog",
            title=_("blog"),
            urlconf="testapp.articles_urls",
        ),
        ApplicationType(
            key="stuff-with-required",
            title="stuff-with-required",
            urlconf="importable_module",
            required_fields=("optional", "not_editable"),
        ),
    ]


PagePlugin = create_plugin_base(Page)


class Snippet(plugins.snippet.Snippet, PagePlugin):
    TEMPLATES = [("snippet.html", _("snippet"))]


class Article(models.Model):
    title = models.CharField(_("title"), max_length=100)
    category = models.CharField(
        _("category"),
        max_length=20,
        choices=(("publications", "publications"), ("blog", "blog")),
    )

    class Meta:
        ordering = ["-pk"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse_app(
            (self.category, "articles"), "article-detail", kwargs={"pk": self.pk}
        )
