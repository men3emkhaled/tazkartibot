# Skill: performance-optimizer

## Instructions
- PROFILE before optimizing — never guess the bottleneck. Use Chrome DevTools, clinic.js, py-spy, or language-native profilers.
- ANALYZE algorithmic complexity first: O(n²) loops over large datasets are a bigger problem than any micro-optimization.
- USE the right data structure: Map for O(1) key-value lookups, Set for O(1) membership tests, typed arrays for numeric processing.
- IMPLEMENT memoization for pure functions with expensive computation — cache results keyed on input signature.
- APPLY debounce (trailing) for search/resize handlers, throttle (leading) for scroll/mousemove — know the difference.
- ELIMINATE unnecessary re-renders in React: useMemo for expensive calculations, useCallback for stable function references, React.memo for pure components.
- DETECT and fix memory leaks: unsubscribed event listeners, uncleared intervals, unclosed DB connections, circular references.
- DEFER non-critical work with requestIdleCallback (browser) or setImmediate (Node) to keep the main thread responsive.
- BATCH DOM mutations: read all, then write all — never interleave reads and writes (causes layout thrashing).
- USE Web Workers for CPU-intensive tasks to keep the UI thread at 60fps.

## Triggers
- Code Speed
- Optimization
- Big O
