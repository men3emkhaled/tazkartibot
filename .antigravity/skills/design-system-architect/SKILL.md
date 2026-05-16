# Skill: design-system

## Instructions
- STRUCTURE tokens in 3 tiers: Primitive (raw values) → Semantic (purpose-driven aliases) → Component (specific usage).
- USE Style Dictionary or Theo to transform tokens from a single JSON source into CSS variables, JS objects, iOS Swift, Android XML.
- DEFINE component API contracts before implementation: props, variants, states, slots, and composition patterns.
- BUILD components at 4 levels: Base (unstyled, accessible) → Styled (design applied) → Composed (multi-component) → Page-level.
- DOCUMENT every component in Storybook with: description, props table, all variant stories, do/don't examples, and accessibility notes.
- ENFORCE the open/closed principle in components: open for extension via props/slots, closed for internal modification.
- VERSION the design system semantically: breaking changes = major, new components = minor, fixes = patch.
- MAINTAIN a decision log (ADR - Architecture Decision Records) for every non-obvious design or API decision.
- BUILD visual regression tests with Chromatic or Percy to catch unintended style changes in CI.
- DEFINE contribution guidelines: naming conventions, file structure, required stories, and review process.

## Triggers
- Design Tokens
- Component Library
- Storybook
- Figma Tokens
- Style Dictionary
