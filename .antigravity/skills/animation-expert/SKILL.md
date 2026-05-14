# Skill: animation-expert

## Instructions
- FOLLOW the 12 principles of animation: squash & stretch, anticipation, follow-through, and easing are most critical for UI.
- USE cubic-bezier curves intentionally: ease-out for elements entering the screen, ease-in for exiting, ease-in-out for state changes.
- TARGET animation durations: micro-interactions 100-200ms, page transitions 250-400ms, complex sequences 400-600ms. Never exceed 700ms for interactive feedback.
- IMPLEMENT View Transitions API for native-feeling page transitions in SPAs and MPAs.
- USE CSS @keyframes with will-change: transform and opacity only — never animate layout-triggering properties (width, height, top, left).
- APPLY the FLIP technique (First, Last, Invert, Play) for performant layout animations.
- USE Framer Motion's layout prop and AnimatePresence for React component enter/exit animations.
- IMPLEMENT spring physics (stiffness, damping, mass) for natural-feeling interactions instead of linear easing.
- ALWAYS respect prefers-reduced-motion: wrap all non-essential animations in a media query check.
- CHAIN animations with AnimationTimeline or GSAP ScrollTrigger for scroll-driven storytelling.
- AVOID animating more than 2-3 properties simultaneously — it creates visual noise, not delight.

## Triggers
- CSS Animation
- Micro-interactions
- GSAP
- Framer Motion
- Motion Design
