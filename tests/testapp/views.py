from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from feincms3.renderer import RegionRenderer, render_in_context

from testapp.models import Page, Snippet


renderer = RegionRenderer()
renderer.register(
    Snippet,
    lambda plugin, context: render_in_context(
        context, plugin.template_name, {"additional": "context"}
    ),
)


def page_detail(request, path=None):
    page = get_object_or_404(
        Page.objects.active(), path=("/%s/" % path) if path else "/"
    )
    page.activate_language(request)

    if url := page.get_redirect_url():
        return HttpResponseRedirect(url)
    return render(
        request,
        page.type.template_name,
        {
            "page": page,
            "regions": renderer.regions_from_item(
                page, inherit_from=page.ancestors().reverse()
            ),
        },
    )
