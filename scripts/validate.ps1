param(
  [string]$SkillCreatorPath = $env:CODEX_SKILL_CREATOR_PATH,
  [string]$PluginCreatorPath = $env:CODEX_PLUGIN_CREATOR_PATH
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot

Push-Location $Root
try {
  Write-Host 'Running public reproducible checks...'
  python -m unittest discover -s tests -v
  python scripts\smoke_eval.py
  python skills\ceo-thread-orchestrator\scripts\validate_cmmd_exchange.py --check-schemas
  python skills\ceo-thread-orchestrator\scripts\validate_pipeline.py skills\ceo-thread-orchestrator\templates\pipeline.yaml --json
  python skills\ceo-thread-orchestrator\scripts\scorecard_handoff.py skills\ceo-thread-orchestrator\templates\typed_handoff.yaml --json
  python skills\ceo-thread-orchestrator\scripts\scorecard_handoff.py skills\ceo-thread-orchestrator\templates\review_handoff.yaml --json
  python scripts\check_release_state.py

  if ($SkillCreatorPath) {
    $SkillValidator = Join-Path $SkillCreatorPath 'scripts\quick_validate.py'
    python $SkillValidator (Join-Path $Root 'skills\ceo-thread-orchestrator')
  } else {
    Write-Host 'Optional skill validation skipped: set CODEX_SKILL_CREATOR_PATH to the skill-creator directory.'
  }

  if ($PluginCreatorPath) {
    $PluginValidator = Join-Path $PluginCreatorPath 'scripts\validate_plugin.py'
    python $PluginValidator $Root
  } else {
    Write-Host 'Optional plugin validation skipped: set CODEX_PLUGIN_CREATOR_PATH to the plugin-creator directory.'
  }
} finally {
  Pop-Location
}
