# Agent Simulation Engine — Android

## Purpose

This directory contains the Android development plan and
acceptance criteria for the Agent Simulation Engine.

The target is an installable Android application capable of
running an open-weight language model locally on the device.

## Current milestone

The Android build workflow downloads the official llama.cpp
Android example and builds a proof-of-concept APK.

This APK is a runtime validation artifact. It is not yet the
finished Agent Simulation Engine application.

## Intended architecture

- Native Android application
- On-device LLM inference
- Device-aware model recommendations
- Local model storage
- Local persistent agent memory
- Boss agent and specialist agents
- Shared task orchestration
- Creator-controlled approval gate
- Offline operation after model installation

## Model execution

The initial inference implementation will use llama.cpp
and compatible GGUF models.

Model files should be stored in application-managed storage
after the user selects or downloads a compatible model.

The application must not silently download a model that
exceeds the device's available memory.

## Privacy

Local inference should not require an external AI API.

Network access may still be needed for model downloads,
software updates and explicitly requested research.

The application must clearly distinguish local inference
from external network activity.

## Existing engine

The Python implementation remains the reference engine
during migration.

Do not delete or replace the existing agents, memory,
tools, approvals or runtime implementation merely to
create the Android project.

## Next milestone

Integrate the native inference layer with the existing
agent architecture and create the application's own UI.