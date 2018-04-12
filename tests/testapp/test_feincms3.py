from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import set_urlconf
from django.utils import six
from django.utils.translation import deactivate_all, override

from feincms3.apps import (
    NoReverseMatch, apps_urlconf, reverse, reverse_any, reverse_fallback,
)
from feincms3_sites.middleware import apps_urlconf_for_site
from feincms3_sites.models import Site

from .models import Article, Page


def zero_management_form_data(prefix):
    return {
        '%s-TOTAL_FORMS' % prefix: 0,
        '%s-INITIAL_FORMS' % prefix: 0,
        '%s-MIN_NUM_FORMS' % prefix: 0,
        '%s-MAX_NUM_FORMS' % prefix: 1000,
    }


def merge_dicts(*dicts):
    res = {}
    for d in dicts:
        res.update(d)
    return res


class Test(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            'admin', 'admin@test.ch', 'blabla')
        deactivate_all()

        self.test_site = Site.objects.create(
            host='testserver',
        )

    def login(self):
        client = Client()
        client.force_login(self.user)
        return client

    def test_add_empty_page(self):
        """Add a page without content, test path generation etc"""
        client = self.login()

        response = client.post(
            '/admin/testapp/page/add/',
            merge_dicts(
                {
                    'title': 'Home EN',
                    'slug': 'home-en',
                    'path': '/en/',
                    'site': self.test_site.pk,
                    'static_path': 1,
                    'language_code': 'en',
                    'application': '',
                    'is_active': 1,
                    'menu': 'main',
                    'template_key': 'standard',
                },
                zero_management_form_data('testapp_snippet_set'),
            ),
        )

        self.assertRedirects(
            response,
            '/admin/testapp/page/',
        )

        page = Page.objects.get()
        self.assertEqual(page.slug, 'home-en')
        self.assertEqual(page.path, '/en/')  # static_path!
        self.assertEqual(page.site, self.test_site)

        response = client.get(page.get_absolute_url())
        self.assertContains(
            response,
            '<h1>Home EN</h1>',
            1,
        )

        response = client.post(
            '/admin/testapp/page/add/',
            merge_dicts(
                {
                    'title': 'subpage 1',
                    'slug': 'subpage-1',
                    'parent': page.pk,
                    # 'site': self.test_site.pk,
                    'language_code': 'en',
                    'application': '',
                    'is_active': 1,
                    'menu': 'main',
                    'template_key': 'standard',
                },
                zero_management_form_data('testapp_snippet_set'),
            ),
        )

        self.assertRedirects(
            response,
            '/admin/testapp/page/',
        )

        subpage1 = Page.objects.latest('id')
        self.assertEqual(subpage1.path, '/en/subpage-1/')
        # Site has been set to parent's site
        self.assertEqual(subpage1.site, self.test_site)

        site = Site.objects.create(host='testserver2')
        response = client.post(
            '/admin/testapp/page/add/',
            merge_dicts(
                {
                    'title': 'subpage 2',
                    'slug': 'subpage-2',
                    'parent': page.pk,
                    'site': site.pk,  # Wrong!
                    'language_code': 'en',
                    'application': '',
                    'is_active': 1,
                    'menu': 'main',
                    'template_key': 'standard',
                },
                zero_management_form_data('testapp_snippet_set'),
            ),
        )

        self.assertRedirects(
            response,
            '/admin/testapp/page/',
        )

        subpage2 = Page.objects.latest('id')
        self.assertEqual(subpage2.path, '/en/subpage-2/')
        # Site has been reset to parent's site
        self.assertEqual(subpage2.site, self.test_site)

    def test_apps(self):
        """Article app test (two instance namespaces, two languages)"""

        home_de = Page.objects.create(
            title='home',
            slug='home',
            path='/de/',
            static_path=True,
            language_code='de',
            is_active=True,
            menu='main',
            site=self.test_site,
        )
        home_en = Page.objects.create(
            title='home',
            slug='home',
            path='/en/',
            static_path=True,
            language_code='en',
            is_active=True,
            menu='main',
            site=self.test_site,
        )

        for root in (home_de, home_en):
            for app in ('blog', 'publications'):
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
            for category in ('publications', 'blog'):
                Article.objects.create(
                    title='%s %s' % (category, i),
                    category=category,
                )

        self.assertContains(
            self.client.get('/de/blog/all/'),
            'class="article"',
            7,
        )
        self.assertContains(
            self.client.get('/de/blog/?page=2'),
            'class="article"',
            2,
        )
        self.assertContains(
            self.client.get('/de/blog/?page=42'),
            'class="article"',
            2,  # Last page with instances (2nd)
        )
        self.assertContains(
            self.client.get('/de/blog/?page=invalid'),
            'class="article"',
            5,  # First page
        )

        response = self.client.get('/de/blog/')
        self.assertContains(
            response,
            'class="article"',
            5,
        )

        response = self.client.get('/en/publications/')
        self.assertContains(
            response,
            'class="article"',
            5,
        )

        article = Article.objects.order_by('pk').first()
        with override('de'):
            self.assertEqual(
                article.get_absolute_url(),
                '/de/publications/%s/' % article.pk,
            )

        with override('en'):
            self.assertEqual(
                article.get_absolute_url(),
                '/en/publications/%s/' % article.pk,
            )

        response = self.client.get('/de/publications/%s/' % article.pk)
        self.assertContains(
            response,
            '<h1>publications 0</h1>',
            1,
        )

        # The exact value of course does not matter, just the fact that the
        # value does not change all the time.
        self.assertEqual(
            apps_urlconf(),
            'urlconf_fe9552a8363ece1f7fcf4970bf575a47',
        )

    def test_snippet(self):
        """Check that snippets have access to the main rendering context
        when using TemplatePluginRenderer"""

        home_en = Page.objects.create(
            title='home',
            slug='home',
            path='/en/',
            static_path=True,
            language_code='en',
            is_active=True,
            menu='main',
            site=self.test_site,
        )

        home_en.testapp_snippet_set.create(
            template_name='snippet.html',
            ordering=10,
            region='main',
        )

        response = self.client.get(home_en.get_absolute_url())
        self.assertContains(
            response,
            '<h2>snippet on page home (/en/)</h2>',
            1,
        )
        self.assertContains(
            response,
            '<h2>context</h2>',
            1,
        )

    def test_reverse(self):
        """Test all code paths through reverse_fallback and reverse_any"""

        self.assertEqual(
            reverse_fallback('test', reverse, 'not-exists'),
            'test',
        )
        self.assertEqual(
            reverse_fallback('test', reverse, 'admin:index'),
            '/admin/',
        )
        self.assertEqual(
            reverse_any((
                'not-exists',
                'admin:index',
            )),
            '/admin/',
        )
        with six.assertRaisesRegex(
                self,
                NoReverseMatch,
                "Reverse for any of 'not-exists-1', 'not-exists-2' with"
                " arguments '\[\]' and keyword arguments '{}' not found."
        ):
            reverse_any(('not-exists-1', 'not-exists-2'))

    def test_redirects(self):
        page1 = Page.objects.create(
            title='home',
            slug='home',
            path='/de/',
            static_path=True,
            language_code='de',
            is_active=True,
            site=self.test_site,
        )
        page2 = Page.objects.create(
            title='something',
            slug='something',
            path='/something/',
            static_path=True,
            language_code='de',
            is_active=True,
            redirect_to_page=page1,
            site=self.test_site,
        )
        page3 = Page.objects.create(
            title='something2',
            slug='something2',
            path='/something2/',
            static_path=True,
            language_code='de',
            is_active=True,
            redirect_to_url='http://example.com/',
            site=self.test_site,
        )

        self.assertRedirects(
            self.client.get(page2.get_absolute_url()),
            page1.get_absolute_url(),
        )

        self.assertRedirects(
            self.client.get(page3.get_absolute_url(), follow=False),
            'http://example.com/',
            fetch_redirect_response=False,
        )

        # Everything fine in clean-land
        self.assertIs(page2.clean(), None)

        # Both redirects cannot be set at the same time
        self.assertRaises(
           ValidationError,
           lambda: Page(
                title='test',
                slug='test',
                language_code='de',
                redirect_to_page=page1,
                redirect_to_url='nonempty',
                site=self.test_site,
            ).full_clean(),
        )

        # No chain redirects
        self.assertRaises(
           ValidationError,
           lambda: Page(
                title='test',
                slug='test',
                language_code='de',
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
            title='blog',
            slug='blog',
            static_path=False,
            language_code='en',
            is_active=True,
            application='blog',
            site=Site.objects.create(host='testserver2')
        )
        a = Article.objects.create(
            title='article',
            category='blog',
        )

        # No urlconf.
        self.assertRaises(
            NoReverseMatch,
            a.get_absolute_url,
        )

        # No apps on this site
        self.assertEqual(
            apps_urlconf_for_site(self.test_site),
            'testapp.urls',
        )
        # Apps on this site
        self.assertEqual(
            apps_urlconf_for_site(page.site),
            'urlconf_01c07a48384868b2300536767c9879e2',
        )

        try:
            set_urlconf('urlconf_01c07a48384868b2300536767c9879e2')
            self.assertEqual(
                a.get_absolute_url(),
                '/blog/%s/' % a.pk,
            )

        finally:
            set_urlconf(None)
