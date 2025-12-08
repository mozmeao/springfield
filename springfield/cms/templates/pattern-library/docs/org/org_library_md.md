# Pattern Library

The Django Pattern Library is used to preview and test components (similar to Storybook).

**View it**: [http://localhost:8000/pattern-library/](http://localhost:8000/pattern-library/)

#### Pattern Library Organization

Flare components are organized into three sections:

1. **Base Styles** - Typography, theme variables, and inherited styles
2. **Components** - Component examples and variations
3. **Pages** - Full page layouts combining components

#### Adding Examples

- Create matching `.html` and `.yaml` files with the same name in `/springfield/cms/templates/pattern-library/{section}/**/{example_name}.{html|yaml}`
- Use `<include>` and `<content>` to map YAML data to components
- Loop through parameter options to show multiple variants
- See [button_variants.html](/springfield/springfield/cms/templates/pattern-library/components/button/button_variants.html) for a good example

Learn more: [Pattern Library - Defining Template Context](https://torchbox.github.io/django-pattern-library/guides/defining-template-context/)

> **Note**: Springfield uses [the Lincoln Loop fork of Django Pattern Library](https://github.com/lincolnloop/django-pattern-library).
