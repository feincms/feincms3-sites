from django.utils.functional import lazy

from feincms3_sites.utils import sites_tags


def test_sites(rf):
    request = rf.get('/')
    assert str(sites_tags(request=request)) == '''\
<sites property="og:type" content="website">
  <sites name="description" content="">'''

    lazy_url = lazy(lambda: '/', str)()
    assert str(sites_tags(url=lazy_url, request=request)) == '''\
<sites property="og:type" content="website">
  <sites property="og:url" content="http://testserver/">
  <sites name="description" content="">'''
