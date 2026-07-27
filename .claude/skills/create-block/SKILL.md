---
name: create-block
description: Create a new CMS block
---

## Blocks

CMS blocks are defined at `springfield/cms/blocks.py`.
Templates are located at `springfield/cms/templates/cms/blocks/`.
The blocks are organized by their size and placement. Simpler blocks (equivalent to atoms) come first, followed by the more complex ones that used them (roughly molecules) and the section-level blocks, which fill the page's length. Page-specific blocks are grouped by page.

## Components

CMS blocks should use the HTML components defined at `springfield/cms/templates/components/`. The components are rendered by the `django-includecontents` library.
Components should have all their variants documented in the Pattern Library at `springfield/cms/templates/pattern-library`. The `springfield/cms/templates/pattern-library/docs` has the instructions on how the components architecture works.
When creating a new block, the corresponding component should be built first if it doesn't exist and added to the Pattern Library.
If a block uses multiple components, all of those need to be represented individually on the pattern library, as well as their combination used by the block.

## Fixtures

Fixtures are located at `springfield/cms/fixtures/`.
When new blocks use other inner blocks that already have fixtures, use data from those other fixtures so that the fixtures file corresponding to the external block only has code that's easier to follow. For example, get buttons from the buttons fixture.
Use the block's text fields, such as headings and content, to describe the block's options and behaviors. Be concise and objective. When the field is intended for slightly longer text use the space to be a bit more descriptive.
Add enough variations to cover all the block's options - not necessarily all the possible combinations because there might be too many for a comprehensive page.
For blocks available to the `FreeFormPage2026`, the block variants should be added both to the upper and lower content fields of the page.

Page fixtures should be added to the `springfield/cms/management/commands/load_page_fixtures.py` command.

## Tests

Block unit tests are located ad `springfield/cms/tests/test_blocks.py`.
It's important that the tests verify that all the content fields from the block are properly rendered and that block settings are respected on the HTML.
When blocks use components that have important attributes such as buttons, all those attributes should be verified on the tests. See buttons and image assertions, for example.
Use the custom assertion methods for components that show up in multiple blocks.
Every single field in a block must be fully tested. It means not only testing that the HTML element exists, but also that it's content corresponds to the content from the block data. If the block or the component sets a data attribute to the HTML tag, that attribute must be tested. When testing headings, the test must use the right heading tag to retrieve the element to ensure that the headings hierarchy is correct on the page.

## Visual regression tests

Playwright visual regression tests are located at `tests/playwright/specs/visual-regression`.
Tests should cover light and dark modes.

## Important considerations

Blocks that include headings or buttons should consider the `block_level`, `block_position` and `block_text` template variables.
Those variables are set at the page template level (`springfield/cms/templates/cms/free_form_page2026.html` for example) and get modified by the blocks down the rendering cascade.
Every block that includes a heading and has child blocks that can also contain headings should increment the `block_level` variable so that the child blocks render the correct heading hierarchy. Tests should verify that the correct heading tags are used.
The `block_position` and `block_text` variables are used to build button and link analytics attributes.
All blocks that include headings should set the `block_text` attribute so that buttons' and links' `data-cta-text` include a reference to the nearest heading.
All blocks that include child blocks need to append to the `block_position` attribute so that buttons' and links' `data-cta-position` get the correct location string.
See `springfield/cms/templates/cms/blocks/sections/section.html`, `springfield/cms/templates/cms/blocks/cards-list.html` and `springfield/cms/templates/cms/blocks/icon-card-2026.html`, for example.

Use the instructions to build the block: $ARGUMENTS
Follow these steps to do it:

1. Build the include components, if necessary
2. Add the components to the pattern library, if necessary
3. Create the block
4. Create testing fixtures
5. Create unit tests
6. Create visual regression tests

First present the plan to the user with a simple explanation of what will be done. Allow the user to give feedback before starting the implementation.
