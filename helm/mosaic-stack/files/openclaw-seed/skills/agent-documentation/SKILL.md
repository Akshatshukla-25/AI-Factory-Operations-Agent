---
name: agent-documentation
description: Explain this agent's architecture, integrations, configuration and execution boundaries using its bundled product documentation and deployment profile.
---

<!-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Agent documentation

The product's Markdown documentation is bundled under `skills/agent-documentation/docs`
in the agent workspace. In OpenShell, locate the copied references with sandbox-local
`exec` before reading them; workspace copy locations can vary:

```sh
find /sandbox -type f -path '*/skills/agent-documentation/docs/README.md'
```

Use the returned file's directory as the documentation root. Start with `README.md`,
`docs/installation.md`, `docs/security_model.md`, or `docs/multitenancy.md` as appropriate.

Read `../deployment.json` relative to that documentation root for this installation's module settings, release,
namespace and configured Kubernetes cluster names. Documentation describes supported
behavior; it does not establish that an integration is enabled, reachable or authorized.
Use the current session's registered tools and runtime context to establish available
capabilities, and their results for live state. Sandbox-local binaries and server-side
integration tools are separate execution environments; inspect the registered tools
before concluding that an infrastructure capability is unavailable.

Base Command Manager manuals remain under `skills/bcm/docs` when that module is enabled.
