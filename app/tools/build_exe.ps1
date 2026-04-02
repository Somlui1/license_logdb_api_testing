<#
.SYNOPSIS
    Script for converting install.ps1 to install.exe using the ps2exe module.
    This script will check for the module and install it if missing.

.DESCRIPTION
    The Bootstrapper Installer needs to be an executable for easier distribution.
    This utility automates the conversion process.
#>

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$InputFile = Join-Path $ScriptDir "install.ps1"
$OutputFile = Join-Path $ScriptDir "install.exe"

# 1. Check for PS2EXE module
Write-Host "[*] Checking for ps2exe module..." -ForegroundColor Cyan
if (-not (Get-Module -ListAvailable -Name ps2exe)) {
    Write-Host "[!] ps2exe module not found. Attempting to install..." -ForegroundColor Yellow
    try {
        Install-Module -Name ps2exe -Scope CurrentUser -Force -AllowClobber
        Write-Host "[OK] ps2exe installed successfully." -ForegroundColor Green
    }
    catch {
        Write-Error "Failed to install ps2exe module. Please run as Administrator or install manually: Install-Module -Name ps2exe"
        exit 1
    }
}

# 2. Convert to EXE
Write-Host "[*] Converting $InputFile to $OutputFile..." -ForegroundColor Cyan

$Params = @{
    InputFile   = $InputFile
    OutputFile  = $OutputFile
    Title       = "Bootstrapper Installer v2.0"
    Description = "Dynamic Setup via API"
    Company     = "IT Support"
    Product     = "Bootstrapper Installer"
    Copyright   = "2024 IT Support"
    # NoConsole = $false # We need console for interactive menu
}

try {
    Invoke-PS2EXE @Params
    Write-Host "[SUCCESS] Executable created at: $OutputFile" -ForegroundColor Green
}
catch {
    Write-Error "Conversion failed: $($_.Exception.Message)"
    exit 1
}
