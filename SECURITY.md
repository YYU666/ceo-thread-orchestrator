# Security Policy

CEO Flow is a Codex plugin/skill. It does not intentionally collect credentials, call external services by itself, or require secrets to run.

## Reporting Security Issues

Please open a private GitHub security advisory if available, or open an issue with sanitized details if the report does not expose sensitive information.

Do not post:

- API keys or tokens;
- private repository names;
- private local paths;
- full unsanitized chat transcripts;
- internal workflow names or secrets;
- screenshots containing credentials.

## Supported Versions

This project is experimental. Security and safety fixes are applied to the latest public release.

## Scope

In scope:

- instructions that could cause unsafe file edits;
- instructions that leak private paths or secrets;
- unsafe delegation or automation guidance;
- overly broad permissions in bundled plugin metadata.

Out of scope:

- behavior caused by unrelated local Codex settings;
- third-party model outages;
- private workflow scripts outside this repository.
