import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from feincms3.pages import AbstractPage as BasePage


class SiteQuerySet(models.QuerySet):
    def for_host(self, host):
        default = None
        for site in self.order_by('-is_default'):
            if re.match(site.host_re, host):
                return site
            elif site.is_default:
                default = site
        return default


class Site(models.Model):
    is_default = models.BooleanField(
        _('is default'),
        default=False,
    )
    host = models.CharField(
        _('host'),
        max_length=200,
    )
    is_managed_re = models.BooleanField(
        _('manage the host regex'),
        default=True,
        help_text=_('Deactivate this to specify the regex yourself.'),
    )
    host_re = models.CharField(
        _('host regular expression'),
        max_length=200,
        blank=True,
    )

    objects = SiteQuerySet.as_manager()

    class Meta:
        verbose_name = _('site')
        verbose_name_plural = _('sites')

    def __str__(self):
        return self.host

    def clean(self):
        if self.is_default:
            if self.__class__._base_manager.filter(
                Q(is_default=True),
                ~Q(pk=self.pk),
            ).exists():
                raise ValidationError(
                    _('Only one site can be the default site.'),
                )

    def save(self, *args, **kwargs):
        if self.is_managed_re:
            self.host_re = r'^%s$' % re.escape(self.host)
        super().save(*args, **kwargs)
    save.alters_data = True


class SiteForeignKey(models.ForeignKey):
    def formfield(self, **kwargs):
        kwargs['required'] = False
        return super().formfield(**kwargs)


class AbstractPage(BasePage):
    site = SiteForeignKey(
        Site,
        on_delete=models.CASCADE,
        verbose_name=_('sites'),
        related_name='+',
    )
    # Exactly the same as BasePage.path,
    # except that it is not unique:
    path = models.CharField(
        _('path'),
        max_length=1000,
        blank=True,
        help_text=_('Generated automatically if \'static path\' is unset.'),
        validators=[
            RegexValidator(
                regex=r'^/(|.+/)$',
                message=_('Path must start and end with a slash (/).'),
            ),
        ],
    )

    class Meta:
        abstract = True
        unique_together = (('site', 'path'),)
        verbose_name = _('page')
        verbose_name_plural = _('pages')

    def save(self, *args, **kwargs):
        if self.parent_id and self.parent.site_id:
            self.site_id = self.parent.site_id
        super().save(*args, **kwargs)
    save.alters_data = True

    '''
    def get_absolute_url(self):
        """
        Return the page's absolute URL using ``reverse()``

        If path is ``/``, reverses ``pages:root`` without any arguments,
        alternatively reverses ``pages:page`` with an argument of ``path``.
        Note that this ``path`` is not the same as ``self.path`` -- slashes
        are stripped from the beginning and the end of the string to make
        building an URLconf more straightforward.
        """
        if self.path == '/':
            return reverse('pages:root')
        return reverse('pages:page', kwargs={
            'path': self.path.strip('/'),
        })
    '''
