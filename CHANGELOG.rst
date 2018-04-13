==========
Change log
==========

`Next version`_
~~~~~~~~~~~~~~~

- Added documentation (README only for now).
- Made ``AppsMiddleware`` raise a 404 error if no site matches the
  current requests' host.
- Added a ``SiteMiddleware`` for using feincms3-sites without feincms3
  apps.
- Fixed a bug where creating a root page without a site would crash
  insteaf of showing the field required validation error.
- Fixed the ``verbose_name`` of the site foreign key (it only points to
  a single site).


`0.1`_ (2018-04-12)
~~~~~~~~~~~~~~~~~~~

- Initial release!


.. _0.1: https://github.com/matthiask/feincms3-sites/commit/e19c1ebef0
.. _0.2: https://github.com/matthiask/feincms3-sites/compare/0.1...0.2
.. _Next version: https://github.com/matthiask/feincms3-sites/compare/0.1...master
