import contextvars
import re
import sys
from contextlib import contextmanager
from urllib.parse import urljoin

from asgiref.local import Local
from django.conf import settings
from django.conf.urls.i18n import is_language_prefix_patterns_used
from django.core.exceptions import ImproperlyConfigured
from django.core.signals import request_finished
from django.http import Http404, HttpResponsePermanentRedirect, HttpResponseRedirect
from django.urls import get_script_prefix, is_valid_path
from django.utils.cache import patch_vary_headers
from django.utils.encoding import iri_to_uri
from django.utils.translation import (
    activate,
    get_language,
    get_language_from_path,
    get_language_from_request,
)
from feincms3 import applications
from feincms3.applications import _del_apps_urlconf_cache, apps_urlconf, reverse_app

# must use this import, do not change
from feincms3_sites.utils import get_site_model


_current_site = contextvars.ContextVar("current_site", default=None)
_sites = contextvars.ContextVar("sites", default={})


def site_for_host(host, *, sites=None):
    """
    Return a site instance for the passed host, or ``None`` if there is no
    match and no default site.

    The default site's host regex is tested first.
    """

    if sites is None:
        sites = get_site_model()._default_manager.active()
    default = None
    for site in sorted(sites, key=lambda site: (-site.is_default, site.pk)):
        if re.search(site.host_re, host):
            return site
        elif site.is_default:
            default = site
    return default


def _get_sites():
    return _sites.get() or {
        site.pk: site for site in get_site_model()._default_manager.active()
    }


def build_absolute_uri(url, *, site=None):
    site = site or current_site()
    if hasattr(site, "pk"):
        site = site.pk
    if site and (obj := _get_sites().get(site)):
        return iri_to_uri(urljoin(obj.get_absolute_url(), url))
    return url


def _del_reverse_site_cache(**kwargs):
    _reverse_site_cache.cache = {}


_reverse_site_cache = Local()
request_finished.connect(_del_reverse_site_cache)


def reverse_site_app(*args, site, **kwargs):
    if not hasattr(_reverse_site_cache, "cache"):  # pragma: no cover
        _reverse_site_cache.cache = {}
    key = site.pk if hasattr(site, "pk") else site

    if (urlconf := _reverse_site_cache.cache.get(key)) and urlconf in sys.modules:
        kwargs["urlconf"] = urlconf
    else:
        apps = applications._APPS_MODEL._default_manager.active(
            site=site
        ).applications()
        kwargs["urlconf"] = _reverse_site_cache.cache[key] = apps_urlconf(apps=apps)
    return build_absolute_uri(reverse_app(*args, **kwargs), site=site)


@contextmanager
def set_current_site(site):
    token = _current_site.set(site)
    _del_apps_urlconf_cache()
    yield
    _current_site.reset(token)
    _del_apps_urlconf_cache()


def current_site():
    return _current_site.get()


@contextmanager
def set_sites(sites):
    token = _sites.set(sites)
    yield
    _sites.reset(token)


def site_middleware(get_response):
    site_model = get_site_model()

    def middleware(request):
        sites = site_model._default_manager.active()
        if site := site_for_host(request.get_host(), sites=sites):
            sites = {site.pk: site for site in sites}
            with set_sites(sites), set_current_site(site):
                return get_response(request)
        raise Http404("No configuration found for %r" % request.get_host())

    return middleware


def redirect_to_site_middleware(get_response):
    def middleware(request):
        site = current_site()
        if not site:
            raise ImproperlyConfigured(
                "Current site unknown. Insert site_middleware before redirect_to_site_middleware."
            )

        # Host matches, and either no HTTPS enforcement or already HTTPS
        if request.get_host() == site.get_host() and (
            not settings.SECURE_SSL_REDIRECT or request.is_secure()
        ):
            return get_response(request)

        redirect_class = (
            HttpResponseRedirect if settings.DEBUG else HttpResponsePermanentRedirect
        )
        return redirect_class(
            "http{}://{}{}".format(
                "s" if (settings.SECURE_SSL_REDIRECT or request.is_secure()) else "",
                site.get_host(),
                request.get_full_path(),
            )
        )

    return middleware


def default_language_middleware(get_response):
    def middleware(request):
        site = current_site()
        if not site:
            raise ImproperlyConfigured(
                "Current site unknown. Insert site_middleware before default_language_middleware."
            )

        urlconf = getattr(request, "urlconf", settings.ROOT_URLCONF)
        (
            i18n_patterns_used,
            prefixed_default_language,
        ) = is_language_prefix_patterns_used(urlconf)

        language = None
        if i18n_patterns_used:
            language = get_language_from_path(request.path_info)
        if language is None:
            language = site.default_language or get_language_from_request(request)

        activate(language)
        request.LANGUAGE_CODE = get_language()

        response = get_response(request)

        if (
            response.status_code == 404
            and i18n_patterns_used
            and prefixed_default_language
        ):
            language_path = f"/{language}{request.path_info}"
            path_valid = is_valid_path(language_path, urlconf)
            path_needs_slash = not path_valid and (
                settings.APPEND_SLASH
                and not language_path.endswith("/")
                and is_valid_path("%s/" % language_path, urlconf)
            )

            if path_valid or path_needs_slash:
                script_prefix = get_script_prefix()
                # Insert language after the script prefix and before the
                # rest of the URL
                language_url = request.get_full_path(
                    force_append_slash=path_needs_slash
                ).replace(script_prefix, f"{script_prefix}{language}/", 1)
                # Redirect to the language-specific URL as detected by
                # get_language_from_request(). HTTP caches may cache this
                # redirect, so add the Vary header.
                redirect = HttpResponseRedirect(language_url)
                patch_vary_headers(redirect, ("Accept-Language", "Cookie"))
                return redirect

        # Maybe not necessary, but do not take chances.
        patch_vary_headers(response, ("Accept-Language",))
        response.setdefault("Content-Language", get_language())
        return response

    return middleware
