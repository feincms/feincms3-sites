import re

from django.conf import global_settings, settings
from django.core.checks import Error
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import signals
from django.utils.translation import gettext_lazy as _
from feincms3 import pages
from feincms3.utils import ChoicesCharField

from feincms3_sites.middleware import current_site, site_for_host
from feincms3_sites.utils import import_callable


_language_names = dict(global_settings.LANGUAGES)

if not hasattr(settings, "FEINCMS3_SITES_SITE_MODEL"):  # pragma: no cover
    settings.FEINCMS3_SITES_SITE_MODEL = "feincms3_sites.Site"
if not hasattr(settings, "FEINCMS3_SITES_SITE_GET_HOST"):  # pragma: no cover
    settings.FEINCMS3_SITES_SITE_GET_HOST = None


class SiteQuerySet(models.QuerySet):
    """
    Return a site instance for the passed host, or ``None`` if there is no
    match and no default site.

    The default site's host regex is tested first.
    """

    def active(self):
        return self.filter(is_active=True)

    def for_host(self, host):
        return site_for_host(host, sites=self)


def validate_language_codes(value):
    if value:
        known = {code for code, _name in settings.LANGUAGES}
        if unknown := {code for code in value.split(",") if code not in known}:
            raise ValidationError(
                _("Unknown language codes: {}").format(", ".join(sorted(unknown)))
            )


class AbstractSite(models.Model):
    is_active = models.BooleanField(_("is active"), default=True)
    is_default = models.BooleanField(_("is default"), default=False)
    host = models.CharField(_("host"), max_length=200)
    is_managed_re = models.BooleanField(
        _("manage the host regex"),
        default=True,
        help_text=_("Deactivate this to specify the regex yourself."),
    )
    host_re = models.CharField(_("host regular expression"), max_length=200, blank=True)
    default_language = ChoicesCharField(
        _("default language"),
        max_length=10,
        blank=True,
        choices=global_settings.LANGUAGES,
        help_text=_(
            "The default language will be overridden by more specific settings"
            " such as the language of individual pages."
        ),
    )
    language_codes = models.CharField(
        _("language codes"),
        max_length=200,
        blank=True,
        help_text=_("A list of comma-separated langauge codes supported by this site."),
        validators=[validate_language_codes],
    )

    objects = SiteQuerySet.as_manager()

    class Meta:
        abstract = True
        verbose_name = _("site")
        verbose_name_plural = _("sites")

    def __str__(self):
        return self.host

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    save.alters_data = True

    def get_absolute_url(self):
        protocol = "https:" if settings.SECURE_SSL_REDIRECT else "http:"
        return f"{protocol}//{self.get_host()}"

    def clean(self):
        if self.is_managed_re:
            self.host_re = r"^%s$" % re.escape(self.host)

        try:
            match = re.search(self.host_re, self.host)
        except Exception as exc:
            raise ValidationError(
                _("Error while validating the regular expression: %s") % exc
            ) from exc
        else:
            if not match:
                raise ValidationError(
                    _("The regular expression does not match the host.")
                )

    def get_host(self):
        return self.host

    def languages(self):
        return (
            [
                (code, _language_names.get(code, ""))
                for code in self.language_codes.split(",")
            ]
            if self.language_codes
            else settings.LANGUAGES
        )


def _prepare_site_model(sender, **kwargs):
    if issubclass(sender, AbstractSite) and (
        spec := settings.FEINCMS3_SITES_SITE_GET_HOST
    ):
        AbstractSite.get_host = import_callable(spec)


signals.class_prepared.connect(_prepare_site_model)


class Site(AbstractSite):
    class Meta(AbstractSite.Meta):
        swappable = "FEINCMS3_SITES_SITE_MODEL"


class SiteForeignKey(models.ForeignKey):
    """
    The site foreign key field should not be required, so that we can fill in
    a value from the parent.
    """

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return name, "django.db.models.ForeignKey", args, kwargs

    def formfield(self, **kwargs):
        kwargs["required"] = False
        return super().formfield(**kwargs)


class AbstractPageQuerySet(pages.AbstractPageQuerySet):
    def active(self, *, site=None):
        return self.filter(is_active=True, site=site or current_site())


class AbstractPage(pages.AbstractPage):
    # Exactly the same as BasePage.path,
    # except that it is not unique:
    path = models.CharField(
        _("path"),
        max_length=1000,
        blank=True,
        help_text=_("Generated automatically if 'static path' is unset."),
        validators=[
            RegexValidator(
                regex=r"^/(|.+/)$",
                message=_("Path must start and end with a slash (/)."),
            )
        ],
    )

    objects = AbstractPageQuerySet.as_manager(with_tree_fields=True)

    class Meta:
        abstract = True
        ordering = ["position"]
        unique_together = (("site", "path"),)
        verbose_name = _("page")
        verbose_name_plural = _("pages")

    def _clash_candidates(self):
        return super()._clash_candidates().filter(site=self.site_id)

    def clean_fields(self, exclude=None):
        """
        Since the ``SiteForeignKey`` adds ``required=False`` we have to add
        our own check here.
        """
        exclude = [] if exclude is None else exclude
        super().clean_fields(exclude)

        if not self.site_id and not self.parent_id:
            # Using validation_error() does not work as it should, because
            # 'site' is always part of exclude, because the model field is
            # required, but the form field is not, therefore Django adds
            # 'site' into 'exclude' unconditionally.
            raise ValidationError(_("The site is required when creating root nodes."))

    def save(self, *args, **kwargs):
        if self.parent_id and self.parent.site_id:
            self.site_id = self.parent.site_id
        super().save(*args, **kwargs)

    save.alters_data = True

    @staticmethod
    def add_site_field(sender, **kwargs):
        if issubclass(sender, AbstractPage) and not sender._meta.abstract:
            from feincms3_sites.utils import get_site_model

            SiteForeignKey(
                get_site_model(),
                on_delete=models.CASCADE,
                verbose_name=_("site"),
                related_name="+",
            ).contribute_to_class(sender, "site")

    @classmethod
    def check(cls, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(cls._check_feincms3_sites_page(**kwargs))
        return errors

    @classmethod
    def _check_feincms3_sites_page(cls, **kwargs):
        unique_together = [set(fields) for fields in cls._meta.unique_together]
        if {"site", "path"} not in unique_together:
            yield Error(
                "Models using the feincms3-sites page must ensure that paths exist only once per site.",
                obj=cls,
                id="feincms3_sites.E001",
                hint='Add ("site", "path") to unique_together.',
            )


models.signals.class_prepared.connect(AbstractPage.add_site_field)
