from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.test import Client, TestCase
from django.test.utils import override_settings
from django.urls import set_urlconf
from django.utils import six
from django.utils.translation import deactivate_all, override

from feincms3.apps import NoReverseMatch, reverse, reverse_any, reverse_fallback
from feincms3_sites.middleware import apps_urlconf_for_site
from feincms3_sites.models import Site

from .models import Article, Page


def zero_management_form_data(prefix):
    return {
        "%s-TOTAL_FORMS" % prefix: 0,
        "%s-INITIAL_FORMS" % prefix: 0,
        "%s-MIN_NUM_FORMS" % prefix: 0,
        "%s-MAX_NUM_FORMS" % prefix: 1000,
    }


def merge_dicts(*dicts):
    res = {}
    for d in dicts:
        res.update(d)
    return res


@override_settings(
    MIDDLEWARE=settings.MIDDLEWARE + ["feincms3_sites.middleware.apps_middleware"]
)
class AppsMiddlewareTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("admin", "admin@test.ch", "blabla")
        deactivate_all()

        self.test_site = Site.objects.create(host="testserver", is_default=True)

    def login(self):
        client = Client()
        client.force_login(self.user)
        return client

    def test_add_empty_page(self):
        """Add a page without content, test path generation etc"""
        client = self.login()

        response = client.post(
            "/admin/testapp/page/add/",
            merge_dicts(
                {
                    "title": "Home EN",
                    "slug": "home-en",
                    "path": "/en/",
                    "site": self.test_site.pk,
                    "static_path": 1,
                    "language_code": "en",
                    "application": "",
                    "is_active": 1,
                    "menu": "main",
                    "template_key": "standard",
                },
                zero_management_form_data("testapp_snippet_set"),
            ),
        )

        self.assertRedirects(response, "/admin/testapp/page/")

        page = Page.objects.get()
        self.assertEqual(page.slug, "home-en")
        self.assertEqual(page.path, "/en/")  # static_path!
        self.assertEqual(page.site, self.test_site)

        response = client.get(page.get_absolute_url())
        self.assertContains(response, "<h1>Home EN</h1>", 1)

        response = client.post(
            "/admin/testapp/page/add/",
            merge_dicts(
                {
                    "title": "subpage 1",
                    "slug": "subpage-1",
                    "parent": page.pk,
                    # 'site': self.test_site.pk,
                    "language_code": "en",
                    "application": "",
                    "is_active": 1,
                    "menu": "main",
                    "template_key": "standard",
                },
                zero_management_form_data("testapp_snippet_set"),
            ),
        )

        self.assertRedirects(response, "/admin/testapp/page/")

        subpage1 = Page.objects.get(slug="subpage-1")
        self.assertEqual(subpage1.path, "/en/subpage-1/")
        # Site has been set to parent's site
        self.assertEqual(subpage1.site, self.test_site)

        site = Site.objects.create(host="testserver2")
        response = client.post(
            "/admin/testapp/page/add/",
            merge_dicts(
                {
                    "title": "subpage 2",
                    "slug": "subpage-2",
                    "parent": page.pk,
                    "site": site.pk,  # Wrong!
                    "language_code": "en",
                    "application": "",
                    "is_active": 1,
                    "menu": "main",
                    "template_key": "standard",
                },
                zero_management_form_data("testapp_snippet_set"),
            ),
        )

        self.assertRedirects(response, "/admin/testapp/page/")

        subpage2 = Page.objects.get(slug="subpage-2")
        self.assertEqual(subpage2.path, "/en/subpage-2/")
        # Site has been reset to parent's site
        self.assertEqual(subpage2.site, self.test_site)

    def test_validation_with_sites(self):
        other_site_page = Page.objects.create(
            title="bla",
            slug="bla",
            path="/de/sub/",
            static_path=True,
            site=Site.objects.create(host="testserver3"),
        )
        root = Page.objects.create(
            title="bla", slug="bla", path="/de/", static_path=True, site=self.test_site
        )
        sub = Page.objects.create(title="sub", slug="sub", parent=root)

        # Reload pages to fetch CTE data
        other_site_page, root, sub = list(Page.objects.order_by("id"))

        other_site_page.full_clean()
        sub.full_clean()
        root.full_clean()

        self.assertEqual(other_site_page.path, sub.path)

    def test_root_without_site(self):
        """Create a root page without selecting a site instance should show
        validation errors"""
        client = self.login()
        response = client.post(
            "/admin/testapp/page/add/",
            merge_dicts(
                {
                    "title": "Home EN",
                    "slug": "home-en",
                    "path": "/en/",
                    # 'site': self.test_site.pk,
                    "static_path": 1,
                    "language_code": "en",
                    "application": "",
                    "is_active": 1,
                    "menu": "main",
                    "template_key": "standard",
                },
                zero_management_form_data("testapp_snippet_set"),
            ),
        )
        # print(response.content.decode('utf-8'))
        self.assertContains(response, "The site is required when creating root nodes.")

    def test_apps(self):
        """Article app test (two instance namespaces, two languages)"""

        home_de = Page.objects.create(
            title="home",
            slug="home",
            path="/de/",
            static_path=True,
            language_code="de",
            is_active=True,
            menu="main",
            site=self.test_site,
        )
        home_en = Page.objects.create(
            title="home",
            slug="home",
            path="/en/",
            static_path=True,
            language_code="en",
            is_active=True,
            menu="main",
            site=self.test_site,
        )

        for root in (home_de, home_en):
            for app in ("blog", "publications"):
                Page.objects.create(
                    title=app,
                    slug=app,
                    static_path=False,
                    language_code=root.language_code,
                    is_active=True,
                    application=app,
                    parent_id=root.pk,
                    site=self.test_site,
                )

        for i in range(7):
            for category in ("publications", "blog"):
                Article.objects.create(title="%s %s" % (category, i), category=category)

        self.assertContains(self.client.get("/de/blog/all/"), 'class="article"', 7)
        self.assertContains(self.client.get("/de/blog/?page=2"), 'class="article"', 2)
        self.assertContains(
            self.client.get("/de/blog/?page=42"),
            'class="article"',
            2,  # Last page with instances (2nd)
        )
        self.assertContains(
            self.client.get("/de/blog/?page=invalid"),
            'class="article"',
            5,  # First page
        )

        response = self.client.get("/de/blog/")
        self.assertContains(response, 'class="article"', 5)

        response = self.client.get("/en/publications/")
        self.assertContains(response, 'class="article"', 5)

        set_urlconf(apps_urlconf_for_site(self.test_site))
        try:
            article = Article.objects.order_by("pk").first()
            with override("de"):
                self.assertEqual(
                    article.get_absolute_url(), "/de/publications/%s/" % article.pk
                )

            with override("en"):
                self.assertEqual(
                    article.get_absolute_url(), "/en/publications/%s/" % article.pk
                )
        finally:
            set_urlconf(None)

        response = self.client.get("/de/publications/%s/" % article.pk)
        self.assertContains(response, "<h1>publications 0</h1>", 1)

        # The exact value of course does not matter, just the fact that the
        # value does not change all the time.
        self.assertEqual(
            apps_urlconf_for_site(self.test_site),
            "urlconf_fe9552a8363ece1f7fcf4970bf575a47",
        )

        p = Page.objects.create(
            title="new",
            slug="new",
            path="/bla/",
            static_path=True,
            language_code="en",
            is_active=True,
            application="blog",
            site=Site.objects.create(host="testserver3"),
        )

        self.assertEqual(
            apps_urlconf_for_site(self.test_site),
            "urlconf_fe9552a8363ece1f7fcf4970bf575a47",
        )

        p.site = self.test_site
        p.save()

        self.assertEqual(
            apps_urlconf_for_site(self.test_site),
            "urlconf_da1f83777fa670f709393652c6a2b8ed",
        )

    def test_snippet(self):
        """Check that snippets have access to the main rendering context
        when using TemplatePluginRenderer"""

        home_en = Page.objects.create(
            title="home",
            slug="home",
            path="/en/",
            static_path=True,
            language_code="en",
            is_active=True,
            menu="main",
            site=self.test_site,
        )

        home_en.testapp_snippet_set.create(
            template_name="snippet.html", ordering=10, region="main"
        )

        response = self.client.get(home_en.get_absolute_url())
        self.assertContains(response, "<h2>snippet on page home (/en/)</h2>", 1)
        self.assertContains(response, "<h2>context</h2>", 1)

    def test_reverse(self):
        """Test all code paths through reverse_fallback and reverse_any"""

        self.assertEqual(reverse_fallback("test", reverse, "not-exists"), "test")
        self.assertEqual(reverse_fallback("test", reverse, "admin:index"), "/admin/")
        self.assertEqual(reverse_any(("not-exists", "admin:index")), "/admin/")
        with six.assertRaisesRegex(
            self,
            NoReverseMatch,
            "Reverse for any of 'not-exists-1', 'not-exists-2' with"
            " arguments '\[\]' and keyword arguments '{}' not found.",
        ):
            reverse_any(("not-exists-1", "not-exists-2"))

    def test_redirects(self):
        page1 = Page.objects.create(
            title="home",
            slug="home",
            path="/de/",
            static_path=True,
            language_code="de",
            is_active=True,
            site=self.test_site,
        )
        page2 = Page.objects.create(
            title="something",
            slug="something",
            path="/something/",
            static_path=True,
            language_code="de",
            is_active=True,
            redirect_to_page=page1,
            site=self.test_site,
        )
        page3 = Page.objects.create(
            title="something2",
            slug="something2",
            path="/something2/",
            static_path=True,
            language_code="de",
            is_active=True,
            redirect_to_url="http://example.com/",
            site=self.test_site,
        )

        self.assertRedirects(
            self.client.get(page2.get_absolute_url()), page1.get_absolute_url()
        )

        self.assertRedirects(
            self.client.get(page3.get_absolute_url(), follow=False),
            "http://example.com/",
            fetch_redirect_response=False,
        )

        # Everything fine in clean-land
        self.assertIs(page2.clean(), None)

        # Both redirects cannot be set at the same time
        self.assertRaises(
            ValidationError,
            lambda: Page(
                title="test",
                slug="test",
                language_code="de",
                redirect_to_page=page1,
                redirect_to_url="nonempty",
                site=self.test_site,
            ).full_clean(),
        )

        # No chain redirects
        self.assertRaises(
            ValidationError,
            lambda: Page(
                title="test",
                slug="test",
                language_code="de",
                redirect_to_page=page2,
                site=self.test_site,
            ).full_clean(),
        )

        # No redirects to self
        page2.redirect_to_page = page2
        self.assertRaises(ValidationError, page2.full_clean)

    def test_site_apps(self):
        """Test that apps are only available inside their sites"""

        page = Page.objects.create(
            title="blog",
            slug="blog",
            static_path=False,
            language_code="en",
            is_active=True,
            application="blog",
            site=Site.objects.create(host="testserver2"),
        )
        a = Article.objects.create(title="article", category="blog")

        # No urlconf.
        self.assertRaises(NoReverseMatch, a.get_absolute_url)

        # No apps on this site
        self.assertEqual(apps_urlconf_for_site(self.test_site), "testapp.urls")
        # Apps on this site
        self.assertEqual(
            apps_urlconf_for_site(page.site), "urlconf_01c07a48384868b2300536767c9879e2"
        )

        try:
            set_urlconf("urlconf_01c07a48384868b2300536767c9879e2")
            self.assertEqual(a.get_absolute_url(), "/blog/%s/" % a.pk)

        finally:
            set_urlconf(None)

    def test_site_model(self):
        """Test various aspects of the Site model"""
        # No problems
        self.test_site.full_clean()

        self.assertRaises(ValidationError, Site(is_default=True).full_clean)

        s2 = Site.objects.create(host="testserver2", host_re=r"^testserver.*$")

        # No fails.
        s2.full_clean()
        self.assertEqual(str(s2), "testserver2")

        # Overridden
        self.assertEqual(s2.host_re, r"^testserver2$")

        s3 = Site.objects.create(
            host="testserver3", host_re=r"^testserver.*$", is_managed_re=False
        )

        self.assertEqual(s3.host_re, r"^testserver.*$")

        self.assertEqual(Site.objects.for_host("testserver"), self.test_site)
        self.assertEqual(Site.objects.for_host("testserver2"), s2)
        self.assertEqual(Site.objects.for_host("testserver-anything"), s3)
        self.assertEqual(Site.objects.for_host("anything"), self.test_site)

        # No default site:
        self.test_site.delete()
        self.assertEqual(Site.objects.for_host("anything"), None)

    def test_host_re_mismatch(self):
        self.test_site.is_managed_re = False
        self.test_site.host = "testserver2"
        with six.assertRaisesRegex(
            self, ValidationError, r"The regular expression does not match the host."
        ):
            self.test_site.full_clean()

    def test_invalid_host_re(self):
        self.test_site.is_managed_re = False
        self.test_site.host_re = r"^(asdf"  # broken on purpose
        with six.assertRaisesRegex(
            self, ValidationError, "Error while validating the regular expression: "
        ):
            self.test_site.full_clean()

    def test_404(self):
        Page.objects.create(
            title="home",
            slug="home",
            path="/de/",
            static_path=True,
            language_code="de",
            is_active=True,
            site=self.test_site,
        )
        self.assertContains(self.client.get("/de/"), "home - testapp")

        self.test_site.is_default = False
        self.test_site.host = "testserver2"
        self.test_site.save()

        self.assertEqual(self.client.get("/de/").status_code, 404)


@override_settings(
    MIDDLEWARE=settings.MIDDLEWARE + ["feincms3_sites.middleware.site_middleware"]
)
class SiteMiddlewareTest(TestCase):
    def test_404(self):
        test_site = Site.objects.create(host="testserver", is_default=True)
        Page.objects.create(
            title="home",
            slug="home",
            path="/de/",
            static_path=True,
            language_code="de",
            is_active=True,
            site=test_site,
        )
        self.assertContains(self.client.get("/de/"), "home - testapp")

        test_site.is_default = False
        test_site.host = "testserver2"
        test_site.save()

        self.assertEqual(self.client.get("/de/").status_code, 404)


class CanonicalDomainMiddlewareTest(TestCase):
    def setUp(self):
        self.test_site = Site.objects.create(host="example.com", is_default=True)
        Page.objects.create(
            title="home",
            slug="home",
            path="/de/",
            static_path=True,
            language_code="de",
            is_active=True,
            site=self.test_site,
        )


@override_settings(
    MIDDLEWARE=[
        "feincms3_sites.middleware.site_middleware",
        "feincms3_sites.middleware.redirect_to_site_middleware",
    ]
    + settings.MIDDLEWARE
)
class MiddlewareNotUsedTestCase(CanonicalDomainMiddlewareTest):
    def test_request(self):
        self.assertContains(
            self.client.get("/de/", HTTP_HOST="example.com"), "home - testapp"
        )


@override_settings(
    MIDDLEWARE=["feincms3_sites.middleware.redirect_to_site_middleware"]
    + settings.MIDDLEWARE
)
class ImproperlyConfiguredTest(CanonicalDomainMiddlewareTest):
    def test_request(self):
        with six.assertRaisesRegex(
            self, ImproperlyConfigured, 'No "site" attribute on request.'
        ):
            self.client.get("/de/", HTTP_HOST="example.com")


@override_settings(
    MIDDLEWARE=[
        "feincms3_sites.middleware.site_middleware",
        "feincms3_sites.middleware.redirect_to_site_middleware",
    ]
    + settings.MIDDLEWARE
)
class CanonicalDomainTestCase(CanonicalDomainMiddlewareTest):
    def test_http_requests(self):
        response = self.client.get("/", HTTP_HOST="example.org")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "http://example.com/")

        self.assertContains(
            self.client.get("/de/", HTTP_HOST="example.com"), "home - testapp"
        )

    def test_https_requests(self):
        response = self.client.get("/", HTTP_HOST="example.org", secure=True)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "https://example.com/")

        self.assertContains(
            self.client.get("/de/", HTTP_HOST="example.com", secure=True),
            "home - testapp",
        )


@override_settings(
    MIDDLEWARE=[
        "feincms3_sites.middleware.site_middleware",
        "feincms3_sites.middleware.redirect_to_site_middleware",
    ]
    + settings.MIDDLEWARE,
    SECURE_SSL_REDIRECT=True,
)
class CanonicalDomainSecureTestCase(CanonicalDomainMiddlewareTest):
    def test_http_redirects(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "https://example.com/")

        response = self.client.get("/", HTTP_HOST="example.org")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "https://example.com/")

    def test_https_redirects(self):
        response = self.client.get("/", HTTP_HOST="example.org", secure=True)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "https://example.com/")

    def test_match(self):
        self.assertContains(
            self.client.get("/de/", HTTP_HOST="example.com", secure=True),
            "home - testapp",
        )

    def test_other_site(self):
        """SSL redirect happens, but stays on secondary domain"""
        Site.objects.create(host="example.org")
        response = self.client.get("/", HTTP_HOST="example.org")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "https://example.org/")


@override_settings(
    MIDDLEWARE=[
        "django.middleware.security.SecurityMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        # 'django.middleware.locale.LocaleMiddleware',
        # 'feincms3_sites.middleware.site_middleware',
        "feincms3_sites.middleware.default_language_middleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
    ]
)
class ImproperlyConfiguredDLTest(CanonicalDomainMiddlewareTest):
    def test_request(self):
        with six.assertRaisesRegex(
            self, ImproperlyConfigured, 'No "site" attribute on request.'
        ):
            self.client.get("/de/", HTTP_HOST="example.com")


@override_settings(
    MIDDLEWARE=[
        "django.middleware.security.SecurityMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        # 'django.middleware.locale.LocaleMiddleware',
        "feincms3_sites.middleware.site_middleware",
        "feincms3_sites.middleware.default_language_middleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
    ]
)
class DefaultLanguageTest(TestCase):
    def test_language(self):
        site = Site.objects.create(host="example.com", default_language="de")
        self.assertRedirects(
            self.client.get("/", HTTP_HOST=site.host),
            "/de/",
            fetch_redirect_response=False,
        )

        site.default_language = "en"
        site.save()

        self.assertRedirects(
            self.client.get("/", HTTP_HOST=site.host),
            "/en/",
            fetch_redirect_response=False,
        )

        site.default_language = ""
        site.save()

        self.assertRedirects(
            self.client.get("/", HTTP_HOST=site.host, HTTP_ACCEPT_LANGUAGE="de"),
            "/de/",
            fetch_redirect_response=False,
        )

        self.assertRedirects(
            self.client.get("/", HTTP_HOST=site.host, HTTP_ACCEPT_LANGUAGE="fr, en"),
            "/en/",
            fetch_redirect_response=False,
        )

        self.assertRedirects(
            self.client.get("/", HTTP_HOST=site.host, HTTP_ACCEPT_LANGUAGE="fr"),
            "/en/",
            fetch_redirect_response=False,
        )
