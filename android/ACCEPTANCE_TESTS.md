# Android Acceptance Tests

## Milestone 1 — Build

- [ ] GitHub Actions workflow starts successfully.
- [ ] Android Gradle build completes.
- [ ] APK artifact is uploaded.
- [ ] Build failures are visible in GitHub Actions logs.

## Milestone 2 — Genuine local inference

- [ ] APK installs on a compatible Android device.
- [ ] User can select a compatible GGUF model.
- [ ] Model loads into the native inference engine.
- [ ] A new prompt generates a model response.
- [ ] Runtime diagnostics identify the actual model.
- [ ] Inference is confirmed to run locally.
- [ ] Inference works with network access disabled.

## Milestone 3 — Device compatibility

- [ ] Device memory is checked before model loading.
- [ ] Model size and quantisation are displayed.
- [ ] Insufficient memory produces a useful error.
- [ ] Model loading can be cancelled safely.
- [ ] Inference does not freeze the user interface.

## Milestone 4 — Agent integration

- [ ] Existing agent roles are preserved.
- [ ] Boss can receive a general objective.
- [ ] Specialist delegation is verified.
- [ ] Tool execution remains behind existing safeguards.
- [ ] Agent memory is persisted locally.
- [ ] Memory is recovered after an application restart.

## Milestone 5 — Safety

- [ ] Consequential external actions require explicit
      Creator approval.
- [ ] Approval is bound to the exact proposed action.
- [ ] Approval cannot be reused for a different action.
- [ ] Simulation mode cannot execute live transactions.
- [ ] Model output cannot bypass tool permissions.

## Release rule

A successful Android build is not proof of working
inference.

A successful inference test is not proof of working
agent delegation.

Each milestone must be verified independently.