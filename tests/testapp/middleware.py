from django.shortcuts import render
from feincms3.renderer import RegionRenderer, render_in_context
from feincms3.root.middleware import add_redirect_handler, create_page_if_404_middleware

from testapp.models import Page, Snippet


renderer = RegionRenderer()
renderer.register(
    Snippet,
    lambda plugin, context: render_in_context(
        context, plugin.template_name, {"additional": "context"}
    ),
)


@add_redirect_handler
def handler(request, page):
    page.activate_language(request)
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


page_if_404_middleware = create_page_if_404_middleware(
    queryset=lambda request: Page.objects.active(),
    handler=handler,
    language_code_redirect=True,
)
