# MetaName: Setup User Profile
# MetaPriority: 1.0
<#
.SYNOPSIS
    Component: Setup User Profile
.DESCRIPTION
    Downloaded and dot-sourced by install.ps1.
    Exposes: Install-SetupUserProfile

    Tasks:
      1. Add Java security exception site (http://ahebs.aapico.com:8098/)
      2. Install network printer \\agrpt02\TOSHIBA-AAPICO (idempotent)
      3. Configure Thai + English US keyboard layout with Alt+Shift toggle
#>

function Install-SetupUserProfile {
    <#
    .SYNOPSIS
        Sets up user profile: Java security, printer, and keyboard layout.
    #>

    Write-Host ""
    Write-Host "  ================================================================" -ForegroundColor DarkGray
    Write-Host "  Setup User Profile" -ForegroundColor Cyan
    Write-Host "  ================================================================" -ForegroundColor DarkGray
    Write-Host ""

    # Track results per step
    $stepResults = @()

    # ------------------------------------------------------------------
    #  Step 1/3: Java Security - Exception Sites
    # ------------------------------------------------------------------
    Write-Host "  [Step 1/3] Java Security - Exception Sites" -ForegroundColor Yellow
    Write-Host ""

    try {
        $javaUrl = "http://ahebs.aapico.com:8098/"
        $securityDir = Join-Path $env:USERPROFILE "AppData\LocalLow\Sun\Java\Deployment\security"
        $exceptionFile = Join-Path $securityDir "exception.sites"

        # Create directory structure if it doesn't exist
        if (-not (Test-Path $securityDir)) {
            Write-Host "     Creating directory: $securityDir" -ForegroundColor Gray
            New-Item -ItemType Directory -Path $securityDir -Force | Out-Null
        }

        # Create file if it doesn't exist
        if (-not (Test-Path $exceptionFile)) {
            Write-Host "     Creating file: exception.sites" -ForegroundColor Gray
            New-Item -ItemType File -Path $exceptionFile -Force | Out-Null
        }

        # Read current contents and check if URL already exists
        $currentContent = [System.IO.File]::ReadAllText($exceptionFile, [System.Text.Encoding]::UTF8)

        if ($currentContent -match [regex]::Escape($javaUrl)) {
            Write-Host "     URL already exists in exception.sites - skipping" -ForegroundColor DarkGray
        }
        else {
            # Append URL on a new line
            $newLine = if ($currentContent.Length -gt 0 -and -not $currentContent.EndsWith("`n")) { "`r`n" } else { "" }
            [System.IO.File]::AppendAllText($exceptionFile, "$newLine$javaUrl`r`n", [System.Text.Encoding]::UTF8)
            Write-Host "     Added: $javaUrl" -ForegroundColor Green
        }

        Write-Host "     [OK] Java security exception configured" -ForegroundColor Green
        $stepResults += [PSCustomObject]@{ Step = "Java Security"; Status = "OK"; Details = "exception.sites updated" }
    }
    catch {
        Write-Host "     [FAIL] $($_.Exception.Message)" -ForegroundColor Red
        $stepResults += [PSCustomObject]@{ Step = "Java Security"; Status = "FAILED"; Details = $_.Exception.Message }
    }

    Write-Host ""

    # ------------------------------------------------------------------
    #  Step 2/3: Printer Driver -- \\agrpt02\TOSHIBA-AAPICO
    # ------------------------------------------------------------------
    Write-Host "  [Step 2/3] Printer Driver - \\agrpt02\TOSHIBA-AAPICO" -ForegroundColor Yellow
    Write-Host ""

    try {
        $printerPath = "\\agrpt02\TOSHIBA-AAPICO"

        # Check if printer is already installed
        $existingPrinter = Get-Printer -Name $printerPath -ErrorAction SilentlyContinue

        if ($existingPrinter) {
            Write-Host "     Printer already installed - skipping" -ForegroundColor DarkGray
            Write-Host "     [OK] Printer available" -ForegroundColor Green
            $stepResults += [PSCustomObject]@{ Step = "Printer Driver"; Status = "OK"; Details = "Already installed" }
        }
        else {
            Write-Host "     Installing printer: $printerPath ..." -ForegroundColor Gray

            # Test network path accessibility first
            if (-not (Test-Path $printerPath -ErrorAction SilentlyContinue)) {
                Write-Host "     [WARNING] Network path unreachable: $printerPath" -ForegroundColor Yellow
                Write-Host "     Attempting installation anyway ..." -ForegroundColor Gray
            }

            Add-Printer -ConnectionName $printerPath -ErrorAction Stop

            # Verify installation
            $verifyPrinter = Get-Printer -Name $printerPath -ErrorAction SilentlyContinue
            if ($verifyPrinter) {
                Write-Host "     [OK] Printer installed successfully" -ForegroundColor Green
                $stepResults += [PSCustomObject]@{ Step = "Printer Driver"; Status = "OK"; Details = "Installed" }
            }
            else {
                throw "Printer was added but could not be verified"
            }
        }
    }
    catch {
        Write-Host "     [FAIL] $($_.Exception.Message)" -ForegroundColor Red
        $stepResults += [PSCustomObject]@{ Step = "Printer Driver"; Status = "FAILED"; Details = $_.Exception.Message }
    }

    Write-Host ""

    # ------------------------------------------------------------------
    #  Step 3/3: Keyboard Layout -- Thai + English US
    # ------------------------------------------------------------------
    Write-Host "  [Step 3/3] Keyboard Layout - Thai + English US" -ForegroundColor Yellow
    Write-Host ""

    try {
        # --- Preload: set English US (default) + Thai ---
        $preloadPath = "HKCU:\Keyboard Layout\Preload"

        if (-not (Test-Path $preloadPath)) {
            Write-Host "     Creating registry key: Keyboard Layout\Preload" -ForegroundColor Gray
            New-Item -Path $preloadPath -Force | Out-Null
        }

        # 00000409 = English (United States)
        # 0000041E = Thai (Kedmanee)
        Set-ItemProperty -Path $preloadPath -Name "1" -Value "00000409" -Type String -Force
        Set-ItemProperty -Path $preloadPath -Name "2" -Value "0000041E" -Type String -Force

        Write-Host "     Set Preload: 1 = English US (00000409)" -ForegroundColor Gray
        Write-Host "     Set Preload: 2 = Thai (0000041E)" -ForegroundColor Gray

        # --- Remove Substitutes for clean layout (optional cleanup) ---
        $substitutesPath = "HKCU:\Keyboard Layout\Substitutes"
        if (-not (Test-Path $substitutesPath)) {
            New-Item -Path $substitutesPath -Force | Out-Null
        }

        # --- Toggle hotkey: Alt+Shift to switch language ---
        $togglePath = "HKCU:\Keyboard Layout\Toggle"

        if (-not (Test-Path $togglePath)) {
            Write-Host "     Creating registry key: Keyboard Layout\Toggle" -ForegroundColor Gray
            New-Item -Path $togglePath -Force | Out-Null
        }

        # Language Hotkey: 1 = Alt+Shift, 2 = Ctrl+Shift, 3 = None, 4 = Grave Accent (`)
        # Layout Hotkey:   1 = Alt+Shift, 2 = Ctrl+Shift, 3 = None
        # Hotkey:          1 = Alt+Shift, 2 = Ctrl+Shift, 3 = None, 4 = Grave Accent (`)
        Set-ItemProperty -Path $togglePath -Name "Language Hotkey" -Value "4" -Type String -Force
        Set-ItemProperty -Path $togglePath -Name "Hotkey"          -Value "4" -Type String -Force
        Set-ItemProperty -Path $togglePath -Name "Layout Hotkey"   -Value "3" -Type String -Force

        Write-Host "     Set Toggle: Language Hotkey = Grave Accent" -ForegroundColor Gray
        Write-Host "     Set Toggle: Layout Hotkey   = None" -ForegroundColor Gray

        Write-Host "     [OK] Keyboard layout configured (Thai + English US)" -ForegroundColor Green
        $stepResults += [PSCustomObject]@{ Step = "Keyboard Layout"; Status = "OK"; Details = "Thai + EN-US configured" }
    }
    catch {
        Write-Host "     [FAIL] $($_.Exception.Message)" -ForegroundColor Red
        $stepResults += [PSCustomObject]@{ Step = "Keyboard Layout"; Status = "FAILED"; Details = $_.Exception.Message }
    }

    # ------------------------------------------------------------------
    #  Summary
    # ------------------------------------------------------------------
    Write-Host ""
    Write-Host "  ================================================================" -ForegroundColor DarkGray
    Write-Host "  Setup User Profile - Summary" -ForegroundColor White
    Write-Host "  ================================================================" -ForegroundColor DarkGray
    Write-Host ""

    foreach ($r in $stepResults) {
        if ($r.Status -eq "OK") {
            Write-Host "  [OK]   " -NoNewline -ForegroundColor Green
        }
        else {
            Write-Host "  [FAIL] " -NoNewline -ForegroundColor Red
        }
        Write-Host "$($r.Step)" -NoNewline -ForegroundColor White
        Write-Host " - $($r.Details)" -ForegroundColor DarkGray
    }

    $successCount = @($stepResults | Where-Object { $_.Status -eq "OK" }).Count
    $failCount = @($stepResults | Where-Object { $_.Status -ne "OK" }).Count

    Write-Host ""
    if ($failCount -eq 0) {
        Write-Host "  [OK] All $successCount step(s) completed successfully!" -ForegroundColor Green
    }
    else {
        Write-Host "  $successCount succeeded, $failCount failed." -ForegroundColor Yellow
    }

    Write-Host "  ================================================================" -ForegroundColor DarkGray
    Write-Host ""
}

try {
    Install-SetupUserProfile
}
catch {
    Write-Host "[FAIL] $($_.Exception.Message)" -ForegroundColor Red
}
  
