import re

from django.conf import global_settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from feincms3 import pages

from feincms3_sites.middleware import current_site


class SiteQuerySet(models.QuerySet):
    """
    Return a site instance for the passed host, or ``None`` if there is no
    match and no default site.

    The default site's host regex is tested first.
    """

    def for_host(self, host):
        default = None
        for site in self.filter(is_active=True).order_by("-is_default", "pk"):
            if re.search(site.host_re, host):
                return site
            elif site.is_default:
                default = site
        return default


class Site(models.Model):
    is_active = models.BooleanField(_("is active"), default=True)
    is_default = models.BooleanField(_("is default"), default=False)
    host = models.CharField(_("host"), max_length=200)
    is_managed_re = models.BooleanField(
        _("manage the host regex"),
        default=True,
        help_text=_("Deactivate this to specify the regex yourself."),
    )
    host_re = models.CharField(_("host regular expression"), max_length=200, blank=True)
    default_language = models.CharField(
        _("default language"),
        max_length=10,
        blank=True,
        # Not settings.LANGUAGES to avoid migrations for changing choices.
        choices=global_settings.LANGUAGES,
        help_text=_(
            "The default language will be overridden by more specific settings"
            " such as the language of individual pages."
        ),
    )

    objects = SiteQuerySet.as_manager()

    class Meta:
        verbose_name = _("site")
        verbose_name_plural = _("sites")

    def __str__(self):
        return self.host

    def clean(self):
        if self.is_managed_re:
            self.host_re = r"^%s$" % re.escape(self.host)

        try:
            match = re.search(self.host_re, self.host)
        except Exception as exc:
            raise ValidationError(
                _("Error while validating the regular expression: %s") % exc
            )
        else:
            if not match:
                raise ValidationError(
                    _("The regular expression does not match the host.")
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    save.alters_data = True


class SiteForeignKey(models.ForeignKey):
    """
    The site foreign key field should not be required, so that we can fill in
    a value from the parent.
    """

    def formfield(self, **kwargs):
        kwargs["required"] = False
        return super().formfield(**kwargs)


class AbstractPageManager(pages.AbstractPageManager):
    def active(self, *, site=None):
        return self.filter(is_active=True, site=site or current_site())


class AbstractPage(pages.AbstractPage):
    site = SiteForeignKey(
        Site, on_delete=models.CASCADE, verbose_name=_("site"), related_name="+"
    )
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

    objects = AbstractPageManager()

    class Meta:
        abstract = True
        ordering = ["position"]
        unique_together = (("site", "path"),)
        verbose_name = _("page")
        verbose_name_plural = _("pages")

    def _path_clash_candidates(self):
        return self.__class__._default_manager.exclude(
            ~Q(site=self.site_id)
            | Q(pk__in=self.descendants(), static_path=False)
            | Q(pk=self.pk)
        )

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
