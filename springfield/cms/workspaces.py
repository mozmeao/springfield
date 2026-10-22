# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Admin landing pages for content sections, registered with the `register_workspace` hook."""

from collections.abc import Callable
from dataclasses import dataclass

from django.db.models import Q
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from wagtail import hooks
from wagtail.admin.menu import Menu, MenuItem
from wagtail.models import Page


@dataclass(frozen=True)
class WorkspaceLink:
    label: str
    url: str
    icon: str = "link"


@dataclass(frozen=True)
class Workspace:
    slug: str
    label: str
    # None when the section doesn't exist yet; the workspace is then hidden.
    get_root_page: Callable[[], Page | None]
    icon: str = "folder-open-inverse"
    add_page_model: type[Page] | None = None
    add_label: str = ""
    listing_url_name: str = ""
    listing_label: str = _("Browse all")
    root_edit_label: str = ""
    snippet_models: tuple[type, ...] = ()
    get_extra_links: Callable[[Page, object], list[WorkspaceLink]] | None = None
    order: int = 100

    @property
    def url(self):
        return reverse("cms_workspace", args=[self.slug])

    def get_root_translations(self, root):
        return Page.objects.filter(translation_key=root.translation_key).select_related("locale").order_by("locale__language_code")

    def content_queryset(self, root):
        roots = list(self.get_root_translations(root))
        if not roots:
            return Page.objects.none()
        under_a_root = Q()
        for translated_root in roots:
            under_a_root |= Q(path__startswith=translated_root.path, depth__gt=translated_root.depth)
        pages = Page.objects.filter(under_a_root)
        return pages.type(self.add_page_model) if self.add_page_model else pages

    def user_can_access(self, user, root=None):
        root = root or self.get_root_page()
        if root is None or not user.is_authenticated:
            return False
        permissions = root.permissions_for_user(user)
        return permissions.can_edit() or permissions.can_add_subpage()


def get_workspaces():
    return sorted((fn() for fn in hooks.get_hooks("register_workspace")), key=lambda workspace: (workspace.order, workspace.label))


def get_workspace(slug):
    return next((workspace for workspace in get_workspaces() if workspace.slug == slug), None)


class WorkspaceMenuItem(MenuItem):
    def __init__(self, workspace):
        self.workspace = workspace
        super().__init__(workspace.label, workspace.url, name=f"workspace-{workspace.slug}", icon_name=workspace.icon, order=workspace.order)

    def is_shown(self, request):
        return self.workspace.user_can_access(request.user)


class WorkspacesMenu(Menu):
    @cached_property
    def registered_menu_items(self):
        return [WorkspaceMenuItem(workspace) for workspace in get_workspaces()]


workspaces_menu = WorkspacesMenu()
