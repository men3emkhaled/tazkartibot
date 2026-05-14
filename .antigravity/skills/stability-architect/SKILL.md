# Skill: stability-architect

## Instructions
- NEVER delete existing logic, functions, or utility calls unless explicitly requested or redundant.
- ENSURE all new functions are properly invoked/referenced in the appropriate lifecycle or execution paths.
- VERIFY imports and dependencies after modification to prevent "silent" breaks in functionality.
- PRESERVE existing architectural patterns and naming conventions to maintain codebase homogeneity.
- AUDIT the "before" state of a file before committing changes to ensure no unintended deletions occurred.
- VALIDATE that new features do not shadow or overwrite existing critical variables or state.

## Triggers
- Code Safety
- Regression Prevention
- Integrity
