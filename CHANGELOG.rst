==========
Change log
==========

`Next version`_
~~~~~~~~~~~~~~~

- Fixed a bug where path uniqueness was erroneously checked across
  websites.


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
.. _Next version: https://github.com/matthiask/feincms3-sites/compare/0.3...master
