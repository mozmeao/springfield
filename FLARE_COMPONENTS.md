# Flare Components

Flare Components is the custom component library built for use in the Springfield Wagtail CMS.

## Component Anatomy

### File Structure

Components live in `springfield/cms/templates/components/`

Each component is a single Jinja2 template file that:
- Accepts parameters as variables
- Can define content slots using the `contents` namespace
- Uses existing CSS classes from the Flare design system

### Component Inclusion

Components are included using django-includecontents syntax:
- `<include:component-name>` to include a component
- `<content:slot-name>` to pass named content to slots

## Django Pattern Library

The pattern library UI is used to preview and test components in isolation, similar to Storybook.

### Organization

- **Components**: `springfield/cms/templates/pattern-library/components/`
  - Component variants for testing (`.html` + `.yaml` files)
- **Pages**: `springfield/cms/templates/pattern-library/pages/`
  - Full page examples showing components in context

### Page Structure

Each pattern library page consists of:
- Template file (`.html`) - structure using components
- Context file (`.yaml`) - mock data

## CSS Structure

Flare components use utility-first CSS with consistent class naming:
- `fl-*` prefix for component classes
- `heading`, `body`, `subheading` for typography
- Component styles in `springfield/media/css/cms/`

## Dependencies

- **django-includecontents**: [https://github.com/foundation/django-includecontents](https://github.com/foundation/django-includecontents)
- **Jinja2**: [https://jinja.palletsprojects.com/](https://jinja.palletsprojects.com/)
- **Django Pattern Library**: [https://github.com/torchbox/django-pattern-library](https://github.com/torchbox/django-pattern-library)
