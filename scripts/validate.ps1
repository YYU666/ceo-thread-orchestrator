param(
  [string]$SkillCreatorPath = $env:CODEX_SKILL_CREATOR_PATH,
  [string]$PluginCreatorPath = $env:CODEX_PLUGIN_CREATOR_PATH
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot

function Assert-LastExitCode([string]$Step) {
  if ($LASTEXITCODE -ne 0) {
    throw "$Step failed with exit code $LASTEXITCODE"
  }
}

Push-Location $Root
try {
  Write-Host 'Running public reproducible checks...'
  python -m unittest discover -s tests -v
  Assert-LastExitCode 'unit tests'
  python scripts\smoke_eval.py
  Assert-LastExitCode 'smoke eval'
  python skills\ceo-thread-orchestrator\scripts\stack_doctor.py --project-root $Root --no-memory-probe --json
  Assert-LastExitCode 'stack doctor'
  python skills\ceo-thread-orchestrator\scripts\validate_cmmd_exchange.py --check-schemas
  Assert-LastExitCode 'CMMD schema validation'
  python skills\ceo-thread-orchestrator\scripts\validate_pipeline.py skills\ceo-thread-orchestrator\templates\pipeline.yaml --json
  Assert-LastExitCode 'pipeline validation'
  python skills\ceo-thread-orchestrator\scripts\scorecard_handoff.py skills\ceo-thread-orchestrator\templates\typed_handoff.yaml --json
  Assert-LastExitCode 'implementation handoff scorecard'
  python skills\ceo-thread-orchestrator\scripts\scorecard_handoff.py skills\ceo-thread-orchestrator\templates\review_handoff.yaml --json
  Assert-LastExitCode 'review handoff scorecard'
  python scripts\check_release_state.py
  Assert-LastExitCode 'release-state check'

  if ($SkillCreatorPath) {
    $SkillValidator = Join-Path $SkillCreatorPath 'scripts\quick_validate.py'
    python $SkillValidator (Join-Path $Root 'skills\ceo-thread-orchestrator')
    Assert-LastExitCode 'skill validation'
  } else {
    Write-Host 'Optional skill validation skipped: set CODEX_SKILL_CREATOR_PATH to the skill-creator directory.'
  }

  if ($PluginCreatorPath) {
    $PluginValidator = Join-Path $PluginCreatorPath 'scripts\validate_plugin.py'
    python $PluginValidator $Root
    Assert-LastExitCode 'plugin validation'
  } else {
    Write-Host 'Optional plugin validation skipped: set CODEX_PLUGIN_CREATOR_PATH to the plugin-creator directory.'
  }
} finally {
  Pop-Location
}
