import django
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.test import Client, TestCase
from django.test.utils import isolate_apps, override_settings
from django.urls import set_urlconf
from django.utils.translation import deactivate_all, override
from feincms3.applications import NoReverseMatch, _del_apps_urlconf_cache, apps_urlconf

from feincms3_sites.middleware import (
    _del_reverse_site_cache,
    build_absolute_uri,
    set_current_site,
    set_sites,
    site_for_host,
)
from feincms3_sites.models import (
    AbstractPage,
    AbstractSite,
    Site,
    validate_language_codes,
)
from feincms3_sites.utils import get_site_model, import_callable
from testapp.models import Article, CustomSite, Page


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
    MIDDLEWARE=[
        *settings.MIDDLEWARE,
        "feincms3_sites.middleware.site_middleware",
        "feincms3.applications.apps_middleware",
        "testapp.middleware.page_if_404_middleware",
    ]
)
class AppsMiddlewareTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("admin", "admin@test.ch", "blabla")
        deactivate_all()

        self.test_site = Site.objects.create(host="testserver", is_default=True)

        _del_apps_urlconf_cache()
        _del_reverse_site_cache()

    def login(self):
        client = Client()
        client.force_login(self.user)
        return client

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
                    "is_active": 1,
                    "menu": "main",
                    "page_type": "standard",
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
                    page_type=app,
                    parent_id=root.pk,
                    site=self.test_site,
                )

        for i in range(7):
            for category in ("publications", "blog"):
                Article.objects.create(
                    title=f"{category} {i}", category=category, site=self.test_site
                )

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

        with set_current_site(self.test_site):
            set_urlconf(apps_urlconf())
            try:
                article = Article.objects.order_by("pk").first()
                with override("de"):
                    self.assertEqual(
                        article.get_absolute_url(),
                        "http://testserver/de/publications/%s/" % article.pk,
                    )

                with override("en"):
                    self.assertEqual(
                        article.get_absolute_url(),
                        "http://testserver/en/publications/%s/" % article.pk,
                    )
            finally:
                set_urlconf(None)

        response = self.client.get("/de/publications/%s/" % article.pk)
        self.assertContains(response, "<h1>publications 0</h1>", 1)

        # The exact value of course does not matter, just the fact that the
        # value does not change all the time.
        with set_current_site(self.test_site):
            self.assertEqual(apps_urlconf(), "urlconf_fe9552a8363ece1f7fcf4970bf575a47")

        p = Page.objects.create(
            title="new",
            slug="new",
            path="/bla/",
            static_path=True,
            language_code="en",
            is_active=True,
            page_type="blog",
            site=Site.objects.create(host="testserver3"),
        )

        with set_current_site(self.test_site):
            self.assertEqual(apps_urlconf(), "urlconf_fe9552a8363ece1f7fcf4970bf575a47")

        p.site = self.test_site
        p.save()

        with set_current_site(self.test_site):
            self.assertEqual(apps_urlconf(), "urlconf_0ca4c18b8aca69acfe121a9cbbdbd00e")

    def test_site_apps(self):
        """Test that apps are only available inside their sites"""

        page = Page.objects.create(
            title="blog",
            slug="blog",
            static_path=False,
            language_code="en",
            is_active=True,
            page_type="blog",
            site=Site.objects.create(host="testserver2"),
        )
        a = Article.objects.create(
            title="article", category="blog", site=self.test_site
        )

        # No urlconf.
        self.assertRaises(NoReverseMatch, a.get_absolute_url)

        # No apps on this site
        with set_current_site(self.test_site):
            self.assertEqual(apps_urlconf(), "testapp.urls")
        # Apps on this site
        with set_current_site(page.site):
            self.assertEqual(apps_urlconf(), "urlconf_01c07a48384868b2300536767c9879e2")

    def test_reverse_site_app_caching(self):
        """reverse_site_app caches URLconf module names and doesn't repeat queries"""

        Page.objects.create(
            title="blog",
            slug="blog",
            static_path=False,
            language_code="en",
            is_active=True,
            page_type="blog",
            site=self.test_site,
        )
        a1 = Article.objects.create(
            title="article", category="blog", site=self.test_site
        )

        page = Page.objects.create(
            title="blog",
            slug="blog",
            static_path=False,
            language_code="en",
            is_active=True,
            page_type="blog",
            site=Site.objects.create(host="testserver2"),
        )
        a2 = Article.objects.create(title="article", category="blog", site=page.site)

        with self.assertNumQueries(2):
            # 1. pages with apps
            # 2. hosts
            self.assertEqual(
                a1.get_absolute_url(),
                f"http://testserver/blog/{a1.pk}/",
            )

        _del_apps_urlconf_cache()
        _del_reverse_site_cache()

        with set_sites({site.pk: site for site in (self.test_site, page.site)}):
            with self.assertNumQueries(1):
                # 1. pages with apps
                self.assertEqual(
                    a1.get_absolute_url(),
                    f"http://testserver/blog/{a1.pk}/",
                )
            with self.assertNumQueries(0):
                # 0 (apps are already cached)
                self.assertEqual(
                    a1.get_absolute_url(),
                    f"http://testserver/blog/{a1.pk}/",
                )
            with self.assertNumQueries(1):
                # 1. pages with apps for another site
                self.assertEqual(
                    a2.get_absolute_url(),
                    f"http://testserver2/blog/{a2.pk}/",
                )

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

        s4 = Site.objects.create(
            host="example.com", host_re=r"example\.com$", is_managed_re=False
        )
        self.assertEqual(Site.objects.for_host("example.com"), s4)
        self.assertEqual(Site.objects.for_host("www.example.com"), s4)

        # No default site:
        self.test_site.delete()
        self.assertEqual(Site.objects.for_host("anything"), None)

        # Directly use the utility
        self.assertEqual(site_for_host("anything"), None)

    def test_several_default_hosts(self):
        s1 = Site.objects.create(host="testserver1", is_default=True)
        s2 = Site.objects.create(host="testserver2", is_default=True)

        self.assertEqual(Site.objects.for_host("testserver1"), s1)
        self.assertEqual(Site.objects.for_host("testserver2"), s2)

        # Last default site (highest PK) wins. That's not an important design
        # decision, this test just verifies that the behavior doesn't change.
        self.assertEqual(Site.objects.for_host("testserver3"), s2)

    def test_host_re_mismatch(self):
        self.test_site.is_managed_re = False
        self.test_site.host = "testserver2"
        with self.assertRaisesRegex(
            ValidationError, r"The regular expression does not match the host."
        ):
            self.test_site.full_clean()

    def test_invalid_host_re(self):
        self.test_site.is_managed_re = False
        self.test_site.host_re = r"^(asdf"  # broken on purpose
        with self.assertRaisesRegex(
            ValidationError, "Error while validating the regular expression: "
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

    def test_site_foreignkey_deconstruct(self):
        deconstructed = Page._meta.get_field("site").deconstruct()
        self.assertEqual(deconstructed[0], "site")
        self.assertEqual(deconstructed[1], "django.db.models.ForeignKey")

    def test_absolute_uri(self):
        # No site defined
        self.assertEqual(
            build_absolute_uri("/test/"),
            "/test/",
        )

        # Manual
        self.assertEqual(
            build_absolute_uri("/test/", site=self.test_site),
            "http://testserver/test/",
        )
        self.assertEqual(
            build_absolute_uri("/test/", site=self.test_site.pk),
            "http://testserver/test/",
        )
        self.assertEqual(
            build_absolute_uri("http://example.com/test/", site=self.test_site.pk),
            "http://example.com/test/",
        )

        # Context
        with set_current_site(self.test_site):
            self.assertEqual(
                build_absolute_uri("/test/"),
                "http://testserver/test/",
            )
        with set_sites({3: Site(host="blub.example.com")}):
            self.assertEqual(
                build_absolute_uri("/test/", site=3),
                "http://blub.example.com/test/",
            )
        with override_settings(SECURE_SSL_REDIRECT=True):
            self.assertEqual(
                build_absolute_uri("/test/", site=self.test_site),
                "https://testserver/test/",
            )


@override_settings(
    MIDDLEWARE=[
        *settings.MIDDLEWARE_BASE,
        "feincms3_sites.middleware.site_middleware",
        "testapp.middleware.page_if_404_middleware",
    ]
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
        *settings.MIDDLEWARE,
    ]
)
class MiddlewareNotUsedTestCase(CanonicalDomainMiddlewareTest):
    def test_request(self):
        self.assertContains(
            self.client.get("/de/", HTTP_HOST="example.com"), "home - testapp"
        )


@override_settings(
    MIDDLEWARE=[
        "feincms3_sites.middleware.redirect_to_site_middleware",
        *settings.MIDDLEWARE,
    ]
)
class ImproperlyConfiguredTest(CanonicalDomainMiddlewareTest):
    def test_request(self):
        with self.assertRaisesRegex(ImproperlyConfigured, "Current site unknown."):
            self.client.get("/de/", HTTP_HOST="example.com")


@override_settings(
    MIDDLEWARE=[
        "feincms3_sites.middleware.site_middleware",
        "feincms3_sites.middleware.redirect_to_site_middleware",
        *settings.MIDDLEWARE,
    ]
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

    @override_settings(DEBUG=True)
    def test_debug(self):
        response = self.client.get("/", HTTP_HOST="example.org", secure=True)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://example.com/")


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
        with self.assertRaisesRegex(ImproperlyConfigured, "Current site unknown."):
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
        "testapp.middleware.page_if_404_middleware",
    ]
)
class DefaultLanguageTest(TestCase):
    def test_language(self):
        site = Site.objects.create(host="example.com", default_language="de")
        Page.objects.create(title="en", slug="en", path="/en/", site=site)
        Page.objects.create(title="de", slug="de", path="/de/", site=site)

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

    def test_i18n_patterns(self):
        """i18n_patterns in ROOT_URLCONF work even with apps_middleware"""

        # site = Site.objects.create(host="example.com", default_language="en")
        site = Site.objects.create(host="example.com")

        self.assertRedirects(
            self.client.get("/i18n/", HTTP_HOST=site.host), "/en/i18n/"
        )

        self.assertContains(self.client.get("/en/i18n/", HTTP_HOST=site.host), "en")
        self.assertContains(self.client.get("/de/i18n/", HTTP_HOST=site.host), "de")

        self.assertRedirects(
            self.client.get("/i18n/", HTTP_HOST=site.host, HTTP_ACCEPT_LANGUAGE="de"),
            "/de/i18n/",
        )
        site.default_language = "en"
        site.save()
        self.assertRedirects(
            self.client.get("/i18n/", HTTP_HOST=site.host, HTTP_ACCEPT_LANGUAGE="de"),
            "/en/i18n/",
        )


class SiteTest(TestCase):
    def test_language_codes_validation(self):
        validate_language_codes("")
        validate_language_codes("en,de")
        with self.assertRaisesRegex(ValidationError, "blub"):
            validate_language_codes("blub,de")

        site = Site(language_codes="de")
        self.assertEqual(
            site.languages(),
            [("de", "German")],
        )

        site = Site(language_codes="")
        self.assertEqual(
            site.languages(),
            [("en", "English"), ("de", "German")],
        )


class SiteAdminTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("admin", "admin@test.ch", "blabla")
        deactivate_all()

        self.test_site = Site.objects.create(host="testserver", is_default=True)

    def test_default_language_list_filter(self):
        self.client.login(username="admin", password="blabla")
        response = self.client.get("/admin/feincms3_sites/site/")
        # print(response, response.content.decode("utf-8"))
        self.assertContains(response, "By Default language", 1)
        self.assertContains(
            response,
            '<a href="?default_language=" title="No language">No language</a>'
            if django.VERSION < (4, 1)
            else '<a href="?default_language=">No language</a>',
            1,
        )
        self.assertContains(
            response,
            '<a href="?default_language=en" title="English">English</a>'
            if django.VERSION < (4, 1)
            else '<a href="?default_language=en">English</a>',
            1,
        )
        self.assertContains(
            response,
            '<a href="?default_language=de" title="German">German</a>'
            if django.VERSION < (4, 1)
            else '<a href="?default_language=de">German</a>',
            1,
        )

        response = self.client.get("/admin/feincms3_sites/site/?default_language=en")
        # print(response, response.content.decode("utf-8"))
        self.assertContains(
            response,
            '<li class="selected"><a href="?default_language=en" title="English">English</a></li>'
            if django.VERSION < (4, 1)
            else '<li class="selected"><a href="?default_language=en">English</a></li>',
            1,
            html=True,
        )


class SiteModelTest(TestCase):
    @override_settings(FEINCMS3_SITES_SITE_MODEL="bla")
    def test_invalid_site_model(self):
        with self.assertRaisesRegex(ImproperlyConfigured, "must be of the form"):
            get_site_model()

    @override_settings(FEINCMS3_SITES_SITE_MODEL="not.exists")
    def test_uninstalled_site_model(self):
        with self.assertRaisesRegex(
            ImproperlyConfigured, "that has not been installed"
        ):
            get_site_model()

    @override_settings(
        FEINCMS3_SITES_SITE_MODEL="testapp.CustomSite",
    )
    def test_get_site_model(self):
        self.assertEqual(get_site_model(), CustomSite)

    @override_settings(FEINCMS3_SITES_SITE_MODEL="missing.Model")
    def test_swapped_out_model(self):
        with self.assertRaisesRegex(AttributeError, "Manager isn't available"):
            Site.objects.create(host="testserver", is_default=True)

    def test_import_callable(self):
        from math import ceil

        self.assertEqual(import_callable(ceil), ceil)
        self.assertEqual(import_callable("math.ceil"), ceil)

    @isolate_apps("testapp")
    def test_page_with_missing_unique_together(self):
        """Page subclass without unique_together fails validation"""

        class Page(AbstractPage):
            class Meta:
                unique_together = []

        errors = Page.check()
        error_ids = [error.id for error in errors]
        self.assertIn("feincms3_sites.E001", error_ids)

    @isolate_apps("testapp")
    @override_settings(FEINCMS3_SITES_SITE_GET_HOST=lambda site: "return value")
    def test_custom_get_host(self):
        class MySite(AbstractSite):
            pass

        self.assertEqual(MySite().get_host(), "return value")
