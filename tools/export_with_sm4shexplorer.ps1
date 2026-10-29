param(
    [Parameter(Mandatory=$true)][string]$ExporterExe,
    [Parameter(Mandatory=$true)][string]$GameRoot,
    [Parameter(Mandatory=$true)][string]$WorkRoot,
    [Parameter(Mandatory=$true)][string]$Manifest
)
# Run in 32-bit Windows PowerShell: official Sm4shExplorer 0.07.4 is x86.
$ErrorActionPreference = 'Stop'
if ([Environment]::Is64BitProcess) { throw 'Use 32-bit Windows PowerShell (SysWOW64).' }
$ExporterExe = (Resolve-Path -LiteralPath $ExporterExe).Path
$GameRoot = (Resolve-Path -LiteralPath $GameRoot).Path
$Manifest = (Resolve-Path -LiteralPath $Manifest).Path
$WorkRoot = [IO.Path]::GetFullPath($WorkRoot)
if (Test-Path -LiteralPath $WorkRoot) { throw 'WorkRoot must be a fresh directory; exporter can clean its own export folder.' }
New-Item -ItemType Directory -Path $WorkRoot | Out-Null
foreach ($name in @('plugins','export','extract','temp','workspace')) { New-Item -ItemType Directory -Path (Join-Path $WorkRoot $name) | Out-Null }
$assembly = [Reflection.Assembly]::LoadFrom($ExporterExe)
$cfgType = $assembly.GetType('Sm4shFileExplorer.Objects.Sm4shMod')
$cfg = [Activator]::CreateInstance($cfgType)
foreach ($property in $cfgType.GetProperties()) {
    if ($property.PropertyType.IsGenericType -and $property.CanWrite) { $property.SetValue($cfg,[Activator]::CreateInstance($property.PropertyType),$null) }
}
$cfg.GamePath=$GameRoot+'\'
$cfg.GameVersion=304
$cfg.GameRegionID=2
$cfg.SkipJunkEntries=$true
$cfg.KeepOriginalFlags=$false
$cfg.ExportWithDateFolder=$false
$cfg.ProjectExportFolder=Join-Path $WorkRoot 'export'
$cfg.ProjectExtractFolder=Join-Path $WorkRoot 'extract'
$cfg.ProjectTempFolder=Join-Path $WorkRoot 'temp'
$cfg.ProjectWorkplaceFolder=Join-Path $WorkRoot 'workspace'
$configFile=Join-Path $WorkRoot 'project.xml'
$serializer=New-Object System.Xml.Serialization.XmlSerializer($cfgType)
$writer=New-Object System.IO.StreamWriter($configFile)
try { $serializer.Serialize($writer,$cfg) } finally { $writer.Close() }
[Environment]::CurrentDirectory=$WorkRoot
Set-Location -LiteralPath $WorkRoot
$projectType=$assembly.GetType('Sm4shFileExplorer.Sm4shProject')
$project=[Activator]::CreateInstance($projectType)
$flags=[Reflection.BindingFlags]'Public,NonPublic,Instance'
$loaded=$projectType.GetMethod('LoadProject',$flags).Invoke($project,[object[]]@([string]$configFile))
if ($null -eq $loaded) { throw 'Cannot load game project.' }
foreach ($item in (Get-Content -LiteralPath $Manifest -Raw | ConvertFrom-Json)) {
    # The manifest is generated locally by prepare_native_candidate.py.
    $project.AddFileToWorkspace([string]$item.source,[string]$item.directory)
}
$build=$projectType.GetMethod('RebuildRFAndPatchlist',$flags,$null,[type[]]@([bool]),$null).Invoke($project,[object[]]@([bool]$true))
if ([string]::IsNullOrWhiteSpace($build)) { throw 'Official export failed; inspect private logs.' }
Write-Output ('OFFICIAL_BUILD='+$build)
