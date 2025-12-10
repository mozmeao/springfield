# Sample component

I'm going to use a component we don't actually have as an example. Let's call it "status" and it is a single word with a background colour.

### 1. Base Template

`/springfield/cms/templates/components/status.html`:

```jinja2
<span class="fl-status">
    {% if contents.body %}
        {{ contents.body }}
    {% endif %}
</span>
```

### 2. Component CSS

`/media/css/cms/flare-status.css`:

```css

:root {
    --fl-status-padding: var(--token-spacing-xs);

    @media (min-width: 600px) {
        --fl-status-padding: var(--token-spacing-sm);
    }

    @media (min-width: 900px) {
        --fl-status-padding: var(--token-spacing-md);
    }
}

.fl-status {
    background-color: var(--fl-theme-orange-bg);
    color: var(--fl-theme-orange-text);
    padding: var(--fl-status-padding);
}
```

`/media/css/cms/flare.css`

```css
@import 'flare-status.css' layer(components);
```

## 3. Wagtail Block

`/springfield/cms/templates/cms/blocks/status.html`

```jinja2
<include:status>
  {% if value.body %}
    <content:body>
      {{ value.body }}
    </content:body>
  {% endif %}
</include:status>
```

### 4. Pattern Library

`/springfield/cms/templates/pattern-library/components/status/status.html`

```jinja2
<include:status
  body="{{ body }}"
/>
```

`/springfield/cms/templates/pattern-library/components/status/status.yaml`

```yaml
name: "Status"
context:
  body: "Passed"
```

#### Variants

`/springfield/cms/templates/pattern-library/components/status/status-variants.html`

```jinja2
<div class="pl-frame pl-frame--white">
  {% for status in statuses %}
      <include:status
        body="{{ status.body }}"
      />
  {% endfor %}
</div>

```

`/springfield/cms/templates/pattern-library/components/status/status-variants.yaml`

```yaml
name: "Status variants"
context:
  statuses:
    - body: 'Passed'
      color: 'green'
    - body: 'Failed'
      color: 'orange'
```


`/springfield/cms/templates/pattern-library/components/status/status-variants.md`

```md
# Template docs

Notes and gotchas for the "template docs" panel go here.
```
