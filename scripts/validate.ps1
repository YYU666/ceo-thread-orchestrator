param(
  [string]$SkillCreatorPath = $env:CODEX_SKILL_CREATOR_PATH,
  [string]$PluginCreatorPath = $env:CODEX_PLUGIN_CREATOR_PATH
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot

if ($SkillCreatorPath) {
  $SkillValidator = Join-Path $SkillCreatorPath 'scripts\quick_validate.py'
  python $SkillValidator (Join-Path $Root 'skills\ceo-thread-orchestrator')
} else {
  Write-Host 'Skipping skill validation: set CODEX_SKILL_CREATOR_PATH to the skill-creator directory.'
}

if ($PluginCreatorPath) {
  $PluginValidator = Join-Path $PluginCreatorPath 'scripts\validate_plugin.py'
  python $PluginValidator $Root
} else {
  Write-Host 'Skipping plugin validation: set CODEX_PLUGIN_CREATOR_PATH to the plugin-creator directory.'
}
