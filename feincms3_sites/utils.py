from django.apps import apps as django_apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def get_site_model():
    """
    Returns the configured site model or the default site model `feincms3_sites.Site`.

    A custom site model can be configured in the settings like so
    ```
    FEINCMS3_SITES_SITE_MODEL = 'myapp.CustomSite'
    ```
    """

    try:
        # make this optional as we do not want to break existing applications
        model_name = "feincms3_sites.site"
        if hasattr(settings, "FEINCMS3_SITES_SITE_MODEL"):
            model_name = getattr(settings, "FEINCMS3_SITES_SITE_MODEL").lower()
        return django_apps.get_model(model_name, require_ready=False)
    except ValueError:
        raise ImproperlyConfigured(
            "FEINCMS3_SITES_SITE_MODEL must be of the form 'app_label.model_name'"
        )
    except LookupError:
        raise ImproperlyConfigured(
            "FEINCMS3_SITES_SITE_MODEL refers to model '%s' that has not been installed"
            % model_name
        )
