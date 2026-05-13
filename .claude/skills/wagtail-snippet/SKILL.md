---
name: wagtail-snippet
description: Guide for creating new Wagtail snippets with page integration in Springfield. Covers model patterns, migrations, templates, JS, tests, and common pitfalls learned from production incidents.
---

# Creating a Wagtail Snippet with Page Integration

Create a new Wagtail snippet following Springfield conventions, based on the name and purpose the user described.

Before writing any code, study the existing patterns:
- **Snippet models:** `springfield/cms/models/snippets.py`
- **Page integration:** `springfield/cms/models/pages.py`
- **Template tags:** `springfield/cms/templatetags/cms_tags.py`
- **Existing tests:** `springfield/cms/tests/` (look at existing snippet tests for reference)

---

## Step 1: Define the Snippet Model

**File:** `springfield/cms/models/snippets.py`

Use the standard mixin chain and register the snippet:

```python
class MySnippet(FluentPreviewableMixin, BaseDraftTranslatableSnippetMixin, models.Model):
    """One-line description of what this snippet does."""

    # Fields
    heading = RichTextField(features=HEADING_TEXT_FEATURES, blank=True)
    # ... add fields with help_text explaining behavior to editors

    panels = [FieldPanel("heading")]

    # Fields that don't change per locale (URLs, images, config values, etc.)
    override_translatable_fields = [SynchronizedField("field_name")]

    class Meta(BaseDraftTranslatableSnippetMixin.Meta):
        verbose_name = "My Snippet"
        verbose_name_plural = "My Snippets"

    def __str__(self):
        from springfield.cms.templatetags.cms_tags import remove_tags
        return f"{remove_tags(richtext(self.heading))} - {self.locale}"

    def get_preview_context(self, request, mode_name):
        # IMPORTANT: If your template needs context beyond `value`/`object`,
        # you MUST override this. Otherwise the preview will crash.
        context = super().get_preview_context(request, mode_name)
        # Build any extra context your template needs
        return context

    def get_preview_template(self, request, mode_name):
        return "cms/snippets/my-snippet-preview.html"

    def clean(self):
        # Add validation here
        return super().clean()


register_snippet(MySnippet)  # Don't forget this!
```

### Key rules:
- Always add `help_text` to fields editors interact with
- Override `get_preview_context()` if your template needs more than just `value`
- Always call `register_snippet()` after the class definition
- Add `clean()` validation for field dependencies (e.g., "at least one of X or Y required")

---

## Step 2: Choose Your Architecture

There are two patterns for connecting snippets to pages. Choose one:

### Pattern A: Template-Tag Only (preferred for simple cases)

The snippet is fetched in the template via a template tag. No `get_context()` needed on pages.

- Page model: just a boolean flag (`show_my_snippet`)
- Template tag: queries snippet by locale
- Template: calls tag, sets `value`, includes snippet template

**Advantages:** Simple, no code duplication across pages, fewer bugs.

### Pattern B: get_context() + Template Tag (for per-page overrides)

The page's `get_context()` builds extra context (e.g., resolved override values). Use this when pages need to customize snippet behavior individually.

- Page model: boolean flag + override fields
- `get_context()`: queries snippet, builds context dict
- Template tag: also queries snippet for `value`
- Template: needs both `value` and the extra context

**Advantages:** Supports per-page customization.
**Risks:** Every page type needs `get_context()`, context can be None, preview needs `get_preview_context()`.

### If using Pattern B:
- Create a shared helper function for the query (avoid duplicating logic)
- **NEVER import from `fixtures/` in production code** -- fixtures use `update_or_create` which writes to DB on every call
- Add None guards in both `get_context()` and the template
- Add the `get_context()` to ALL page types that use the template

---

## Step 3: Add Page Fields

**File:** `springfield/cms/models/pages.py`

```python
# Boolean flag to enable the snippet
show_my_snippet = models.BooleanField(
    default=False,
    help_text="If true, the snippet will be displayed on this page.",
)

# If using per-page overrides (Pattern B):
override_field = models.CharField(
    blank=True,
    help_text="Explain what this overrides and what takes priority.",
)
```

Group override fields in a collapsed panel:

```python
content_panels = [
    ...,
    FieldPanel("show_my_snippet"),
    MultiFieldPanel(
        [FieldRowPanel([
            FieldPanel("override_field"),
        ])],
        heading="My Snippet Overrides",
        classname="collapsed",
    ),
]
```

Add to ALL page types that should support the snippet. Check every page's template to confirm it uses the snippet block.

---

## Step 4: Template Tag

**File:** `springfield/cms/templatetags/cms_tags.py`

```python
@pass_context
@library.global_function
def get_my_snippet(context):
    from springfield.cms.models.snippets import MySnippet

    locale = None
    if "page" in context and hasattr(context["page"], "locale"):
        locale = context["page"].locale
    elif "self" in context and hasattr(context["self"], "locale"):
        locale = context["self"].locale

    if locale:
        return MySnippet.objects.filter(locale=locale).live().first()
    return None
```

This returns one snippet per locale. If you need multiple snippets, use a FK on the page model instead.

---

## Step 5: Templates

**Snippet template** (`cms/snippets/my-snippet.html`):
- Always guard against None context: `{% if value %}` or `{% if extra_context %}`
- Use `{{ value.heading|richtext }}` for rich text fields
- Fix whitespace in tags: `{% if x %}` not `{%if x %}`
- Don't leak raw URLs in alt text

**Preview template** (`cms/snippets/my-snippet-preview.html`):
```html
{% extends "cms/base-flare26.html" %}
{% block content %}
  <div class="fl-main">
    {% set value = object %}
    {% include "cms/snippets/my-snippet.html" %}
  </div>
{% endblock content %}
```

**Page template integration** (in `{% block my_block %}`):
```html
{% if page.show_my_snippet %}
  {% set snippet = get_my_snippet() %}
  {% if snippet %}
    {% set value = snippet %}
    {% include "cms/snippets/my-snippet.html" %}
  {% endif %}
{% endif %}
```

---

## Step 6: JavaScript

If the snippet has interactive behavior:

- **Scope all DOM queries** to the snippet element: `snippetEl.querySelector(...)` not `document.querySelector(...)`
- **Use `js-` prefixed classes** for JS hooks (see Step 12)
- **Cookie/state persistence:** If saving user preferences (e.g., dismissed, collapsed), respect the consent API. Separate "don't auto-show" from "don't attach handlers" — always attach handlers so the user can still interact
- **Avoid state flicker:** If the server can determine the initial state (e.g., via a cookie), pass it to the template in `get_context()` rather than relying on JS to fix it after page load

---

## Step 7: CSS

- Use CSS logical properties (`block-size`, `inline-size`, `inset`) not physical properties
- Use `overflow: hidden` on animated containers to prevent content flash during transitions
- Add `cursor: pointer` on interactive elements
- `@starting-style` is not supported in all browsers -- ensure graceful degradation
- Use design token variables (`--token-*`) not hardcoded colors

---

## Step 8: Migration

### Before creating the migration:
- Remove any fields from the model that you added then removed during development
- The migration should represent the FINAL schema only
- Never create-then-drop a field in the same PR (this has caused production outages)

### Process:
```bash
python manage.py makemigrations cms
```

Then:
1. Add the MPL license header to the generated file
2. Run `ruff check --fix` and `ruff format` on it
3. Break up long lines (especially `field=models.ForeignKey(...)` with help_text)
4. Run `pre-commit run --all-files` to verify

### If main has new migrations:
```bash
git merge origin/main
python manage.py makemigrations --merge --noinput
```

This creates a merge migration -- standard practice in this project. Add the license header and format it.

### Rules:
- One clean migration per feature -- squash if you iterated
- No field drops in the same PR as field adds
- `makemigrations --check --dry-run` must pass before PR
- Run the full test suite before opening a PR, not just your new tests

---

## Step 9: Tests

**File:** `springfield/cms/tests/test_my_snippet.py`

Follow the existing test patterns in `springfield/cms/tests/`:

1. **Unit tests** for resolution/helper logic (use `SimpleNamespace` mocks, no DB)
2. **Validation tests** for `clean()` on snippet and page models
3. **Rendering tests** parametrized across all page types that support the snippet
4. **Template tag tests** for locale lookup, missing snippet, fallback behavior

```python
# Parametrize across all pages that support the feature
PAGES_WITH_MY_SNIPPET = [
    get_thanks_page,
    get_freeform_page_2026_with_snippet,
    get_whats_new_page_with_snippet,
    get_whats_new_page_2026_with_snippet,
]

@pytest.mark.parametrize("get_page_fn", PAGES_WITH_MY_SNIPPET)
def test_snippet_renders_when_flag_on(get_page_fn, minimal_site, rf):
    page = get_page_fn()
    page.show_my_snippet = True
    # ... serve and assert
```

---

## Step 10: Fixtures

**File:** `springfield/cms/fixtures/snippet_fixtures.py`

Create a fixture helper for tests:

```python
def get_my_snippet() -> MySnippet:
    locale = Locale.get_default()
    snippet, _ = MySnippet.objects.update_or_create(
        id=settings.MY_SNIPPET_ID,
        defaults={
            "locale": locale,
            "heading": "<p>Test heading</p>",
            # ... other fields
        },
    )
    return snippet
```

**IMPORTANT:** Fixture helpers are for test setup ONLY. Never import them in production code (models, views, template tags). They use `update_or_create` which writes to the DB on every call.

---

## Step 11: DB Export

**File:** `bin/export-db-to-sqlite.sh`

New snippet models must be added to the DB export script. If you skip this, prod data exports won't include your snippet and other devs pulling the DB will have missing data.

---

## Step 12: JS Class Naming

Use `js-` prefixed classes for JavaScript hooks instead of styling classes:

```html
<!-- Bad: JS depends on styling class -->
<div class="fl-snippet-close">

<!-- Good: separate JS hook class -->
<div class="fl-snippet-close js-snippet-close">
```

This prevents CSS refactors from breaking JS behavior. Style classes can change freely; `js-` classes are the contract with JavaScript.

---

## Step 13: Scope to the Right Pages

Not every page type needs every feature. Before adding fields and `get_context()` to a page model, verify:
- Does that page type's template actually use the snippet block?
- Is there a real use case for the snippet on that page?
- Older or legacy page types may not need new features

Remove what doesn't belong — unused fields and dead code on page models create confusion and test overhead.

---

## Common Pitfalls

| Pitfall | How to avoid |
|---------|-------------|
| Forgot `register_snippet()` | Snippet won't appear in admin |
| Fixture imported in `get_context()` | DB write on every page load -- use a read-only query |
| Missing `get_context()` on one page type | Template crashes with `UndefinedError` on that page |
| Dead `get_context()` on pages that don't use the feature | Remove it -- check the template chain |
| No `get_preview_context()` | Admin preview crashes if template needs extra context |
| Global JS selectors | Wrong elements get modified if class names are reused |
| Styling classes used as JS hooks | CSS changes break JS -- use `js-` prefixed classes |
| Create-then-drop field in same PR | Can cause outage during deploy -- squash migrations |
| No None guard in template | Crashes when snippet doesn't exist for locale |
| Missing `help_text` on fields | Editors don't understand field behavior or precedence |
| Snippet not in DB export script | Other devs pulling prod data won't have the snippet |
| Feature added to pages that don't need it | Dead code, wasted test coverage, confusing admin UI |
| Template tag needs request but doesn't receive it | Pass `request` explicitly if tag needs cookies or session |
