import inspect

from django import forms
from tree_queries.fields import TreeNodeForeignKey


def _variable_from_stack(name, must_exist=()):
    """
    We want to filter objects related to a particular site so that content
    managers can only select objects from the same site as the object which is
    currently being edited. However, there's no sensible way of passing the
    edited object down to the form or choice field without doing it by hand for
    each and every model admin and inline instance. This isn't just tedious:
    The bigger problem is that errors will happen. Therefore, this helper can
    be used to fetch a variable from any parent frame. Specifying only the
    variable name feels a bit brittle, therefore the additional
    ``must_exist`` argument can be used to require several other variables
    to exist in the matching scope. This still isn't 100% safe but it works
    well enough.
    """

    _sentinel = object()
    # Start inspecting from the caller of the function which called us
    frame = inspect.currentframe().f_back.f_back
    try:
        while frame:
            obj = frame.f_locals.get(name, _sentinel)
            if obj is not _sentinel and all(v in frame.f_locals for v in must_exist):
                return obj
            frame = frame.f_back
    finally:
        # Delete the frame reference to make the GC's job easier
        del frame


class AutomaticSiteRestrictionChoiceField(forms.ModelChoiceField):
    def __init__(self, queryset, *args, **kwargs):
        obj = _variable_from_stack("obj", ("object_id", "to_field"))
        queryset = queryset.filter(site_id=obj.site_id if obj else None)
        super().__init__(queryset, *args, **kwargs)


class AutomaticSiteRestrictionForeignKey(TreeNodeForeignKey):
    """
    The Site foreign key field has to be called ``site`` on all participating objects
    """

    def formfield(self, **kwargs):
        kwargs.setdefault("form_class", AutomaticSiteRestrictionChoiceField)
        return super().formfield(**kwargs)
