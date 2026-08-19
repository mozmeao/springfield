---
name: readability-review
description: Use before declaring a code change complete, and when reviewing a diff, to check Python, Jinja templates and tests against this repo's readability rules — naming, comments and docstrings, license headers, dead references, and test shape. Invoke with /readability-review to review the current diff.
---

# Readability review

This repo's code is read far more often than it is written. This pass catches the
things that make a diff harder to maintain than it needs to be. Run it on your own
work before saying it is done, not only when asked to review someone else's.

## Scope

Default to the working diff:

```bash
git diff -- . ':(exclude)static' ':(exclude)assets'
git diff --staged -- . ':(exclude)static' ':(exclude)assets'
```

If the user names a path, PR or branch, review that instead. Only report on lines the
diff actually touches — do not audit untouched code unless the change made it wrong.

## Checklist

Walk each item over every changed file. For each hit, report `file:line`, the problem
in one line, and the replacement.

### 1. Names

- [ ] No single-letter names (`n`, `i`, `p`) and no abbreviations — `rt_soup` should be
      `rich_text_soup`. Applies to Python *and* Jinja template variables.
- [ ] A leading underscore only on genuinely private class or module members. Module-level
      helpers in migrations, fixtures and tests get plain descriptive names.
- [ ] No name shadowing a stdlib module or builtin (an `html` argument beside `import html`).
- [ ] Any name that needs a comment to explain what it is gets renamed instead.

### 2. Comments and docstrings

- [ ] Docstring says what the function does, its purpose, and anything a caller must know.
      Nothing about implementation history, no justification of the design, no description
      of what other functions do with the result.
- [ ] No comment restates the code. Comments survive only where the logic is genuinely
      non-obvious or a decision would otherwise be second-guessed.
- [ ] Nothing references anything outside the file — spec or plan documents, requirement
      labels (`R5`, `R2`), task numbers, ticket IDs, "the design says…". A comment that
      cannot be understood from its own file is worse than none.

      Rejected — `R5 rule` names nothing a reader of `pages.py` can find:

      ```python
      """Callers say what was selected; working out which exclusions survive
      happens here, so the R5 rule lives in one place."""
      ```

      Replacement:

      ```python
      """Callers pass what was selected, not which exclusions to skip."""
      ```

- [ ] Nothing describes code that no longer exists. This is the most common miss after a
      refactor, and it actively misleads. It also applies to comments copied verbatim out
      of a task brief or plan — state the current rationale, not the state being migrated
      away from. "Null so rows without a topic remain valid" — not "so the repoint from
      Tag doesn't require destroying existing articles".
- [ ] The MPL license header stands alone: license comment, blank line, then a separate
      comment block for the file's own documentation. Jinja `{# #}`, Python `#`, CSS/JS
      `/* */` alike.

### 3. Python

- [ ] Every import at module level. An import inside a function or class needs a comment
      saying why it has to be inline.
- [ ] Nothing left behind: an obsolete branch, flag or helper that the change superseded
      is deleted, not parked next to its replacement.

### 4. Jinja templates

- [ ] Conditional values passed to `<include:component>` attributes use the pure expression
      form, never `{% if %}` inside the attribute string — the includecontents extension
      wraps the latter in `_EscapableValue`, which has no `__bool__` and so is always truthy
      even when it renders empty, silently breaking `{% if attr %}` in the component.

      Wrong:

      ```jinja
      prev_url="{% if has_previous() %}?page={{ previous_page_number() }}{% endif %}"
      ```

      Correct:

      ```jinja
      prev_url="{{ '?page=' ~ previous_page_number() if has_previous() else '' }}"
      ```

### 5. Tests

- [ ] Every assertion describes current behaviour. No assertion that removed behaviour is
      absent ("the badge is no longer rendered", "field X is gone") — it passes forever
      while documenting nothing.
- [ ] Fixtures build only what the test needs. The shared page fixtures in
      `springfield/cms/fixtures/` are for tests that render a full page and assert on the
      HTML; a helper, validation-rule or block-value test gets a small local fixture.
- [ ] No `_get_<element>(soup)` style private helpers. Content checks for one rendered
      element live inside the single test that renders it; separate test functions are for
      orthogonal concerns. Shared component assertions use and extend the module-level
      `assert_*` helpers (`springfield/cms/tests/test_blocks.py`).

## Reporting

Order findings most-significant first — misleading comments and stale references before
naming nits. If the pass is clean, say so plainly in one line; do not invent findings.

Fix the findings when the user asked for a fix or when they are in your own uncommitted
work. Otherwise report and let them choose. If fixes land on work already committed in this
session, amend that commit rather than adding a "fix review comments" commit.
