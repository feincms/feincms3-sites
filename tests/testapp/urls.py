from django.urls import include, re_path
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render

from testapp import views


pages_urlpatterns = (
    [
        re_path(
            r"^$", lambda request: HttpResponseRedirect("/%s/" % request.LANGUAGE_CODE)
        ),
        re_path(r"^(?P<path>[-\w/]+)/$", views.page_detail, name="page"),
        re_path(r"^$", views.page_detail, name="root"),
    ],
    "pages",
)


urlpatterns = i18n_patterns(
    re_path(r"^i18n/$", lambda request: HttpResponse(request.LANGUAGE_CODE))
) + [
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^404/$", lambda request: render(request, "404.html")),
    re_path(r"", include(pages_urlpatterns)),
]
