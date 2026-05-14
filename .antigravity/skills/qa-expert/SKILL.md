# Skill: qa-tester

## Instructions
- FOLLOW the testing pyramid: many unit tests (fast, isolated), fewer integration tests, minimal E2E tests (slow, expensive).
- WRITE tests that document behavior, not implementation — test what the code does, not how it does it internally.
- USE Arrange-Act-Assert (AAA) pattern in every test: clear setup, single action, explicit assertion.
- MOCK external dependencies (HTTP, DB, filesystem) at the boundary — never let tests touch real external services.
- TEST the unhappy path first: null inputs, empty arrays, network errors, auth failures — happy path is easy, edge cases catch bugs.
- ACHIEVE meaningful coverage: 100% line coverage means nothing if critical logical branches aren't tested.
- IMPLEMENT visual regression tests (Playwright screenshots, Storybook + Chromatic) for UI components.
- WRITE contract tests (Pact) for service-to-service integrations — don't rely only on E2E tests for API contracts.
- RUN tests in parallel and in random order — flaky tests that depend on ordering are hiding real bugs.
- ADD tests before fixing bugs: write a failing test that reproduces the bug, then fix it — prevents regression.

## Triggers
- Unit Test
- Integration
- Bug Hunting
