# CSS Architecture

Outlan IPAM uses a modular CSS architecture with theme support and component-based styling.

## File Structure

```
app/static/style/
├── style.css           # Main entry point - imports all modules
├── variables.css       # CSS custom properties and theme definitions
├── components.css      # Reusable UI components (buttons, cards, forms)
├── layout.css          # Page layout and responsive design
└── segment_planner.css # Segment planner page-specific styles
```

## Import Order

`style.css` imports modules in this order:
1. `variables.css` - CSS custom properties
2. `components.css` - Reusable components  
3. `layout.css` - Layout and structure

## Theme System

Three themes controlled via `data-theme` attribute on `<html>`:
- `data-theme="dark"` (default)
- `data-theme="light"`
- `data-theme="midnight"`

Theme colors defined in `variables.css`:
```css
:root { /* dark theme variables */ }
[data-theme="light"] { /* light theme overrides */ }
[data-theme="midnight"] { /* midnight theme overrides */ }
```

## Component System

### Buttons
All buttons inherit from `.btn-base` with variants:
- `.btn-main` - Primary actions
- `.btn-small` - Compact buttons
- `.delete-btn` - Danger actions
- `.save-btn` - Success actions

### Cards
Network blocks and content containers use card components with consistent spacing and styling.

### Forms
Standardized form inputs, labels, and validation styling.

## CSS Variables

Key variable categories:
- `--color-*` - Theme colors
- `--color-bg-*` - Background colors
- `--color-text-*` - Text colors
- Standard spacing and typography scales

## Page-Specific Styles

`segment_planner.css` contains styles specific to the segment planner page and is loaded separately to avoid bloat.

## Responsive Design

Mobile-first approach with breakpoints:
- Base: Mobile styles
- `@media (min-width: 768px)` - Tablet
- `@media (min-width: 1024px)` - Desktop