==========
Change log
==========

Next version
~~~~~~~~~~~~

- Handle the case when a page's site and its parent's site do not match.
- Added Python 3.12, Django 5.0.
- Changed the ``DefaultLanguageListFilter`` to use the model admin's default
  empty value display, and allowed filtering for sites where a default value
  isn't set.


0.20 (2023-11-01)
~~~~~~~~~~~~~~~~~

- Made ``Site.languages`` return all languages instead of nonsense when
  ``language_codes`` is empty.
- Added a system check which ensures that a unique index for ``(site, path)``
  exists on pages.
- Fixed the applications clash check.


0.19 (2023-09-29)
~~~~~~~~~~~~~~~~~

- Started running tests at least once every month.
- Added an optional language codes field which allows defining the list of
  languages per site.
- Added an undocumented ``reverse_site_app`` wrapper around ``reverse_app`` and
  ``build_absolute_uri`` which allows reversing URLs from the current and other
  sites, without caring if a site is active currently.
- Added a default ``get_absolute_url`` method to sites.
- Added an overrideable ``get_host`` method to sites. The method can be
  overridden either in a swappable model or by using the
  ``FEINCMS3_SITES_SITE_GET_HOST`` setting. The setting should be either a
  callable or the Python module path to a callable which accepts the site
  instance and should return a hostname. It's especially useful for local
  development since you can easily change the host values to work in your local
  environment. For example, if you're using feincms3-sites with subdomains you
  could set ``FEINCMS3_SITES_SITE_GET_HOST = lambda site:
  site.host.replace("example.com", "localhost:8000")``.


0.18 (2023-09-08)
~~~~~~~~~~~~~~~~~

- Stopped requiring users of the library to set ``FEINCMS3_SITES_SITE_MODEL``
  themselves if they are happy with the default site model.
- Changed the model definitions to avoid even more migrations because of
  changing choices, hide irrelevant field subclasses.
- Added utilities for only showing objects for some parent object's site in the
  admin interface, see ``feincms3_sites.fields``. Everything is ugly and
  subject to change.
- Stopped calling ``get_site_model`` for each request, once on startup is
  enough.
- Added utilities for building absolute URIs; for example you can now call
  ``feincms3_sites.middleware.build_absolute_uri(url, site=...)`` in your code
  to hopefully add an appropriate protocol and host to a given URL.
- Dropped support for Python 3.8.


0.17 (2023-09-06)
~~~~~~~~~~~~~~~~~

- Stopped ``redirect_to_site_middleware`` from using permanent redirects if
  ``DEBUG`` is ``True``.


0.16 (2023-08-16)
~~~~~~~~~~~~~~~~~

- Added basic support for ``i18n_patterns`` to the
  ``default_language_middleware``.


0.15 (2023-05-30)
~~~~~~~~~~~~~~~~~

- Added Python 3.11, Django 4.2 to the CI. Removed Django 4.0.
- Switched to hatchling and ruff.
- Stopped setting ``request.site``; the current site is available using
  ``current_site()``.


`0.14`_ (2022-08-13)
~~~~~~~~~~~~~~~~~~~~

- Add DefaultLanguageListFilter to limit choices to settings.LANGUAGE
- Add default list_filter to SiteAdmin (is_active, host, default_language)
- Added Python 3.10, Django 4.0 and 4.1 to the CI.
- Raised the requirements to Python >= 3.8, Django >= 3.2.


0.13.1 (2021-10-12)
~~~~~~~~~~~~~~~~~~~

- Fixed exception when using custom site models.


`0.13`_ (2021-10-08)
~~~~~~~~~~~~~~~~~~~~

- The site model is now swappable. (#4, #5)


`0.12`_ (2021-08-12)
~~~~~~~~~~~~~~~~~~~~

- Switched from Travis CI to GitHub actions.
- Updated feincms3-sites for the latest version of feincms3.


`0.11`_ (2020-09-23)
~~~~~~~~~~~~~~~~~~~~

- Raised the minimum supported feincms3 version to 0.38.1.
- Verified compatibility with Django 3.1.
- Dropped compatibility with Django<2.2.


`0.10`_ (2020-01-09)
~~~~~~~~~~~~~~~~~~~~

- Verified compatibility with Django 3.0.
- Replaced ``ugettext*`` with ``gettext*``.


`0.9`_ (2019-09-20)
~~~~~~~~~~~~~~~~~~~

- Removed the requirement to anchor site regular expressions at the
  beginning (meaning that e.g. ``example\.com$`` now works as it
  should).
- Fixed a possible path uniqueness problem with descendants with static
  paths.


`0.8`_ (2019-02-07)
~~~~~~~~~~~~~~~~~~~

- Removed ``apps_urlconf_for_site`` and ``apps_middleware`` since
  feincms3's ``apps_middleware`` now automatically does the right thing
  when used after ``site_middleware``.
- Made the ``site`` argument to ``AbstractPage.objects.active()``
  keyword-only.


`0.7`_ (2019-02-06)
~~~~~~~~~~~~~~~~~~~

- Added an ``is_active`` flag to sites.
- Removed the check that only one site is the default, making it
  possible to change the default through the admin interface.
- Made it possible to edit ``is_active`` and ``is_default`` through the
  changelist.
- Updated the Travis CI configuration to cover a greater range of
  Python and Django version combinations.


`0.6`_ (2019-01-17)
~~~~~~~~~~~~~~~~~~~

- Added validation of the ``host_re`` so that invalid input is catched
  early.
- Sort non-default sites by host in the administration interface.
- Added ordering by ``position`` to the abstract page (necessary for
  newer versions of django-tree-queries).
- Added support for using feincms3-sites without explicitly specifying
  the site everywhere by taking advantage of the upcoming `contextvars
  <https://docs.python.org/3/library/contextvars.html>`__ module and its
  backports.


`0.5`_ (2018-10-02)
~~~~~~~~~~~~~~~~~~~

- Raised test coverage to 100% again.
- Added the possibility to define a default language per site.
- Switched the preferred quote to ``"`` and started using `black
  <https://pypi.org/project/black/>`_ to automatically format Python
  code.


`0.4`_ (2018-04-18)
~~~~~~~~~~~~~~~~~~~

- Fixed a bug where path uniqueness was erroneously checked across
  websites.
- Replaced the default ``Page.objects.active()`` manager method with our
  own ``Page.objects.active(site)`` so that filtering by site is less
  easily forgotten.


`0.3`_ (2018-04-18)
~~~~~~~~~~~~~~~~~~~

- Converted middleware to function-based middleware and renamed them to
  conform to function naming.
- Replaced ``CanonicalDomainMiddleware`` with a
  ``redirect_to_site_middleware`` (which does not inherit any
  functionality from ``SecurityMiddleware`` -- add the
  ``SecurityMiddleware`` yourself).


`0.2`_ (2018-04-17)
~~~~~~~~~~~~~~~~~~~

- Added documentation (README only for now).
- Made ``AppsMiddleware`` raise a 404 error if no site matches the
  current requests' host.
- Added a ``SiteMiddleware`` for using feincms3-sites without feincms3
  apps.
- Fixed a bug where creating a root page without a site would crash
  insteaf of showing the field required validation error.
- Fixed the ``verbose_name`` of the site foreign key (it only points to
  a single site).
- Added a ``CanonicalDomainMiddleware`` which works the same way as the
  middleware in `django-canonical-domain
  <https://github.com/matthiask/django-canonical-domain>`_, except that
  it takes the site from a previous ``AppsMiddleware`` or
  ``SiteMiddleware`` instead of from a ``CANONICAL_DOMAIN`` setting.


`0.1`_ (2018-04-12)
~~~~~~~~~~~~~~~~~~~

- Initial release!


.. _0.1: https://github.com/matthiask/feincms3-sites/commit/e19c1ebef0
.. _0.2: https://github.com/matthiask/feincms3-sites/compare/0.1...0.2
.. _0.3: https://github.com/matthiask/feincms3-sites/compare/0.2...0.3
.. _0.4: https://github.com/matthiask/feincms3-sites/compare/0.3...0.4
.. _0.5: https://github.com/matthiask/feincms3-sites/compare/0.4...0.5
.. _0.6: https://github.com/matthiask/feincms3-sites/compare/0.5...0.6
.. _0.7: https://github.com/matthiask/feincms3-sites/compare/0.6...0.7
.. _0.8: https://github.com/matthiask/feincms3-sites/compare/0.7...0.8
.. _0.9: https://github.com/matthiask/feincms3-sites/compare/0.8...0.9
.. _0.10: https://github.com/matthiask/feincms3-sites/compare/0.9...0.10
.. _0.11: https://github.com/matthiask/feincms3-sites/compare/0.10...0.11
.. _0.12: https://github.com/matthiask/feincms3-sites/compare/0.11...0.12
.. _0.13: https://github.com/matthiask/feincms3-sites/compare/0.12...0.13
.. _0.14: https://github.com/matthiask/feincms3-sites/compare/0.13...0.14
