param(
    [Parameter(Mandatory=$true)][string]$WupsRoot,
    [Parameter(Mandatory=$true)][string]$FunctionPatcherRoot,
    [string]$DevkitProRoot='C:/devkitPro',
    [string]$OutputDirectory='build/aroma-companion'
)
$ErrorActionPreference='Stop'
$workspace=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$WupsRoot=(Resolve-Path -LiteralPath $WupsRoot).Path
$FunctionPatcherRoot=(Resolve-Path -LiteralPath $FunctionPatcherRoot).Path
$DevkitProRoot=(Resolve-Path -LiteralPath $DevkitProRoot).Path
$output=[IO.Path]::GetFullPath((Join-Path $workspace $OutputDirectory))
if (Test-Path -LiteralPath $output) { throw 'Use a fresh output directory.' }
New-Item -ItemType Directory -Path $output | Out-Null
$env:DEVKITPRO=$DevkitProRoot.Replace('\','/')
$env:DEVKITPPC=(Join-Path $DevkitProRoot 'devkitPPC').Replace('\','/')
$cc=Join-Path $DevkitProRoot 'devkitPPC/bin/powerpc-eabi-gcc.exe'
$cxx=Join-Path $DevkitProRoot 'devkitPPC/bin/powerpc-eabi-g++.exe'
$strip=Join-Path $DevkitProRoot 'devkitPPC/bin/powerpc-eabi-strip.exe'
$elf2rpl=Join-Path $DevkitProRoot 'tools/bin/elf2rpl.exe'
$wut=Join-Path $DevkitProRoot 'wut'
$object=Join-Path $output 'main.o'
$elf=Join-Path $output 'HiddenCssGigaRespawn.elf'
$binary=Join-Path $output 'HiddenCssGigaRespawn.wps'
$common=@('-mcpu=750','-meabi','-mhard-float','-ffunction-sections','-fdata-sections')
& $cc @common '-O2' '-Wall' '-Wextra' '-Werror' '-std=gnu11' '-D__WIIU__' '-D__WUT__' '-D__WUPS__' "-ffile-prefix-map=$workspace=." "-I$WupsRoot/include" "-I$FunctionPatcherRoot/include" "-I$wut/include" '-c' (Join-Path $workspace 'companion/main.c') '-o' $object
if ($LASTEXITCODE -ne 0) { throw 'Companion compilation failed.' }
& $cxx @common "-specs=$wut/share/wut.specs" "-specs=$WupsRoot/share/wups.specs" "-T$WupsRoot/share/wups.ld" "-Wl,-Map,$output/companion.map" "-L$WupsRoot/lib" "-L$FunctionPatcherRoot/lib" "-L$wut/lib" $object '-lfunctionpatcher' '-lwups' '-lwut' '-o' $elf
if ($LASTEXITCODE -ne 0) { throw 'Companion linking failed.' }
& $strip '-g' $elf
if ($LASTEXITCODE -ne 0) { throw 'Companion stripping failed.' }
& $elf2rpl $elf $binary
if ($LASTEXITCODE -ne 0) { throw 'Companion conversion failed.' }
$bytes=[IO.File]::ReadAllBytes($binary)
if ($bytes.Length -lt 64 -or $bytes[0] -ne 0x7f -or $bytes[1] -ne 0x45 -or $bytes[2] -ne 0x4c -or $bytes[3] -ne 0x46) { throw 'Unexpected plugin ELF container.' }
# Official WUPS packaging marks the RPL container as a plugin at ELF ident[9:11].
$bytes[9]=0x50
$bytes[10]=0x4c
[IO.File]::WriteAllBytes($binary,$bytes)
Write-Output 'Built experimental Aroma companion; hardware validation is still required.'
