# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from collections import defaultdict
from uuid import UUID

from django.apps import AppConfig


class CmsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "springfield.cms"

    def ready(self):
        # Replace Wagtail's Locale.get_active() with our implementation
        self._patch_locale_get_active()

        # Replace Wagtail's formfield_for_dbfield with our SVG-sanitizing version
        self._patch_image_form_field()

        # Sort hand-translated locales last on the "Translate" locale checkboxes
        self._patch_submit_translation_locale_order()

        # Extend group page permissions to the other locales at their "Translated pages" levels
        self._patch_page_permission_policy()

        # Populate the User Routing signal registry with the v1 signals.
        self._register_routing_signals()

    @staticmethod
    def _register_routing_signals():
        """Populate the routing signal registry.

        Importing the module runs its ``registry.register(...)`` calls exactly once,
        so the registry is ready before any admin surface or resolver reads it.
        """
        # Imported here (not at module top) so registration is tied to app startup
        # rather than to importing this AppConfig.
        from springfield.cms.routing import v1_signals  # noqa: F401

    @staticmethod
    def _patch_locale_get_active():
        """
        Replace Wagtail's Locale.get_active() with Springfield's version.

        This ensures that when Wagtail's routing code calls Locale.get_active(),
        it uses our implementation that normalizes language codes from lowercase
        (e.g., 'en-gb') to mixed-case (e.g., 'en-GB').
        """
        from wagtail.models import Locale

        from springfield.cms.models.locale import SpringfieldLocale

        # Replace the classmethod on the base Locale class
        # We need to use the descriptor protocol properly for classmethods
        Locale.get_active = classmethod(SpringfieldLocale.get_active.__func__)

    @staticmethod
    def _patch_submit_translation_locale_order():
        """
        Sort hand-translated locales last on wagtail-localize's "Translate" form,
        keeping Wagtail's ordering for everything else.

        Wagtail orders locales by `language_code`, which puts Welsh first even though
        an editor rarely picks it. wagtail-localize offers no hook for this, so the
        form is patched here alongside the other startup patches.
        """

        # Imported inline because wagtail-localize's form module pulls in Wagtail
        # models, which cannot be imported while the app registry is still loading.
        from django.conf import settings
        from django.db.models import Case, IntegerField, Value, When

        from wagtail_localize.views.submit_translations import SubmitTranslationForm

        original_init = SubmitTranslationForm.__init__

        def __init__(self, instance, *args, **kwargs):
            original_init(self, instance, *args, **kwargs)

            # Alias locales are excluded from Smartling because they serve another
            # locale's content rather than because anyone translates them by hand,
            # so they keep their usual position.
            all_excluded = getattr(settings, "SMARTLING_EXCLUDED_LOCALES", [])
            hand_translated = [code for code in all_excluded if code not in settings.FALLBACK_LOCALES]
            if not hand_translated:
                return

            locales = self.fields["locales"]
            locales.queryset = locales.queryset.order_by(
                Case(
                    When(language_code__in=hand_translated, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                ),
                "language_code",
            )

        SubmitTranslationForm.__init__ = __init__

    @staticmethod
    def _patch_page_permission_policy():
        """
        Extend a group's page permissions to every translation of the pages they name, at the
        levels the group holds in its "Translated pages" permissions.

        Wagtail scopes a permission to one page and its descendants, and each locale gets
        its own page tree, so a permission below the root reaches a single locale and leaves
        the same page in every other locale unreachable.

        Patching this one method covers the whole admin: the page permission policy,
        ``PagePermissionTester`` and the page explorer all reach their decisions through
        ``get_cached_permissions_for_user``, which reads it. The permissions it adds are
        unsaved, so a group's stored rows stay as the editor entered them.
        """

        # Imported inline because these modules pull in Wagtail models, which cannot be
        # imported while the app registry is still loading.
        from django.contrib.auth.base_user import AbstractBaseUser
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        from wagtail.models import GroupPagePermission, Page
        from wagtail.models.pages import PAGE_PERMISSION_CODENAMES
        from wagtail.permission_policies.pages import PagePermissionPolicy

        from springfield.base.models import TranslatedPagePermission, page_codename

        original_get_all_permissions_for_user = PagePermissionPolicy.get_all_permissions_for_user

        def get_all_permissions_for_user(self: PagePermissionPolicy, user: AbstractBaseUser) -> list[GroupPagePermission]:
            stored_permissions: list[GroupPagePermission] = list(original_get_all_permissions_for_user(self, user))
            if not stored_permissions:
                return stored_permissions

            # Page permission codenames ("publish_page") each group has as "Translated pages" levels
            # {group_id: {"change_page", "publish_page", ...}}
            translated_codenames_by_group: defaultdict[int, set[str]] = defaultdict(set)
            for group_id, translated_codename in Permission.objects.filter(
                group__in={permission.group_id for permission in stored_permissions},
                content_type=ContentType.objects.get_for_model(TranslatedPagePermission),
            ).values_list("group", "codename"):
                translated_codenames_by_group[group_id].add(page_codename(translated_codename))
            if not translated_codenames_by_group:
                return stored_permissions

            page_permissions_by_codename: dict[str, Permission] = {
                permission.codename: permission
                for permission in Permission.objects.filter(content_type__app_label="wagtailcore", codename__in=PAGE_PERMISSION_CODENAMES)
            }

            # The group's own pages keep exactly the levels stored for them, so only the
            # other pages sharing their translation key are extended.
            # { (group_id, translation_key): {fr_page_id, de_page_id, ...} }
            stored_page_ids_by_group_and_key: defaultdict[tuple[int, UUID], set[int]] = defaultdict(set)
            for permission in stored_permissions:
                if permission.group_id in translated_codenames_by_group:
                    stored_page_ids_by_group_and_key[(permission.group_id, permission.page.translation_key)].add(permission.page_id)

            translation_keys: set[UUID] = {translation_key for _group_id, translation_key in stored_page_ids_by_group_and_key}
            pages_by_translation_key: defaultdict[UUID, list[Page]] = defaultdict(list)
            for page in Page.objects.filter(translation_key__in=translation_keys):
                pages_by_translation_key[page.translation_key].append(page)

            return stored_permissions + [
                GroupPagePermission(group_id=group_id, page=page, permission=page_permissions_by_codename[codename])
                for (group_id, translation_key), stored_page_ids in stored_page_ids_by_group_and_key.items()
                for page in pages_by_translation_key[translation_key]
                if page.pk not in stored_page_ids
                for codename in translated_codenames_by_group[group_id]
            ]

        PagePermissionPolicy.get_all_permissions_for_user = get_all_permissions_for_user

    @staticmethod
    def _patch_image_form_field():
        """
        Replace Wagtail's formfield_for_dbfield with our version that uses
        SanitizingWagtailImageField for SVG sanitization.
        This ensures that all image upload forms use our custom field which
        sanitizes SVG files and rejects them if they contain potentially
        dangerous content like scripts or event handlers.
        This is similar to the _patch_locale_get_active approach - we replace
        a Wagtail function with our enhanced version at app startup.
        """

        from django.utils.text import capfirst
        from django.utils.translation import gettext as _

        import wagtail.images.forms
        from wagtail.admin.forms.collections import CollectionChoiceField
        from wagtail.models import Collection

        from springfield.cms.fields import SanitizingWagtailImageField

        def formfield_for_dbfield(db_field, **kwargs):
            """
            Custom formfield callback for image forms with SVG sanitization.
            This replaces Wagtail's default formfield_for_dbfield to use our
            SanitizingWagtailImageField instead of WagtailImageField.
            """
            if db_field.name == "file":
                return SanitizingWagtailImageField(
                    label=capfirst(db_field.verbose_name),
                    **kwargs,
                )
            elif db_field.name == "collection":
                return CollectionChoiceField(
                    label=_("Collection"),
                    queryset=Collection.objects.all(),
                    empty_label=None,
                    **kwargs,
                )

            # For all other fields, use default
            return db_field.formfield(**kwargs)

        # Replace Wagtail's function with ours
        wagtail.images.forms.formfield_for_dbfield = formfield_for_dbfield
