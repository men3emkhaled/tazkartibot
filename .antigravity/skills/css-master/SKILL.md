# Skill: css-master

## Instructions
- USE CSS custom properties (variables) at :root for the full design token system: --color-*, --space-*, --radius-*, --shadow-*, --font-*.
- MASTER the cascade: use @layer to organize styles (reset, base, components, utilities, overrides) with explicit specificity control.
- APPLY fluid typography with clamp(): clamp(1rem, 2.5vw + 0.5rem, 1.5rem) — eliminate media query breakpoints for type.
- USE logical properties (margin-inline, padding-block) for internationalization and RTL support from day one.
- IMPLEMENT :has() selector for parent-state styling instead of JavaScript class toggling where possible.
- USE container queries (@container) for component-level responsiveness instead of viewport-only media queries.
- APPLY the @property rule for type-safe, animatable custom properties with proper syntax, inherits, and initial-value.
- LEVERAGE CSS Grid subgrid for aligning nested elements across parent grid tracks.
- USE :is() and :where() to reduce specificity bloat in complex selectors.
- NEVER use !important except in utility classes where it's intentional — it's a specificity debt sign.
- PREFER gap over margin for spacing in flex/grid contexts. Margin is for flow layout only.
- WRITE CSS that reads like documentation: group related properties, add comments for non-obvious choices.

## Triggers
- CSS
- Grid
- Flexbox
- Custom Properties
- Cascade
