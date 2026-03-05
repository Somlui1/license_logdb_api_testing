<#
.SYNOPSIS
    IT Support Tools Bootstrapper Installer v2.0.0
.DESCRIPTION
    Interactive installer that runs in memory via: irm https://ollama.com/install.ps1 | iex
    Presents a multi-select menu populated dynamically via API,
    downloads choice scripts based on selection, and executes them sequentially sorted by priority.

    Workflow (from instraction.md):
      1. Create folder structure: $env:TEMP\itsupport_tools\{choice, component}
      2. Query API for available choice scripts
      3. Present interactive CLI menu for multi-select
      4. For each selected choice: check local cache -> download if missing -> execute
      5. Execute sequentially sorted by priority (lower number = higher priority)
      6. Show progress bar and summary report

.NOTES
    Author : IT Support DevOps Team
    Version: 2.0.0
#>

# ===========================================================================
#  CONFIGURATION
# ===========================================================================
#http://10.10.3.215:8181/tools/cli-tools/choice
$Script:BaseApiUrl = "http://10.10.3.215:8181/tools/cli-tools/choice"
$Script:BaseScriptUrl = "http://10.10.3.215:8181/tools/cli-tools/choice/download"
$Script:ComponentApiUrl = "http://10.10.3.215:8181/tools/cli-tools/component"
$Script:ComponentDownloadUrl = "http://10.10.3.215:8181/tools/cli-tools/component/download"

# Folder structure per instraction.md:
#   $env:TEMP\itsupport_tools\
#   ├── choice\        <- downloaded choice scripts live here
#   └── component\     <- reserved for component assets
$Script:InstallerDir = Join-Path $env:TEMP "itsupport_tools"
$Script:ChoiceDir = Join-Path $Script:InstallerDir "choice"
$Script:ComponentDir = Join-Path $Script:InstallerDir "component"

# Fast Downloader configuration
$Script:DownloaderUrl = "$Script:ComponentDownloadUrl/fast_downloader.exe"
$Script:DownloaderDir = Join-Path $Script:InstallerDir "tools"
$Script:DownloaderExe = Join-Path $Script:DownloaderDir "fast_downloader.exe"
$Script:DownloaderThreads = 8
# Runtime state
$Script:AvailableChoices = @()

# ===========================================================================
#  HELPER: Show-Status
#  Prints color-coded messages: INFO=Yellow, SUCCESS=Green, ERROR=Red, HINT=Gray
# ===========================================================================
function Show-Status {
    param(
        [Parameter(Mandatory)]
        [string]$Message,

        [Parameter(Mandatory)]
        [ValidateSet("INFO", "SUCCESS", "ERROR", "HINT")]
        [string]$Type
    )

    switch ($Type) {
        "INFO" { Write-Host " [*] $Message" -ForegroundColor Yellow }
        "SUCCESS" { Write-Host " [OK] $Message" -ForegroundColor Green }
        "ERROR" { Write-Host " [!] $Message" -ForegroundColor Red }
        "HINT" { Write-Host "     $Message" -ForegroundColor Gray }
    }
    Start-Sleep -Milliseconds 300
}

# ===========================================================================
#  HELPER: Show-Banner
#  Displays the branded IT SUPPORT header.
# ===========================================================================
function Show-Banner {
    Clear-Host
    $lines = @(
        "   ___    _____             ___             _ __    _ __                    _     ",
        "  |_ _|  |_   _|    o O O  / __|   _  _    | '_ \  | '_ \   ___      _ _   | |_   ",
        "   | |     | |     o       \__ \  | +| |   | .__/  | .__/  / _ \    | '_|  |  _|  ",
        "  |___|   _|_|_   TS__[O]  |___/   \_,_|   |_|__   |_|__   \___/   _|_|_   _\__|  ",
        " _|`"`"`"`"`"|_|`"`"`"`"`"| {======|_|`"`"`"`"`"|_|`"`"`"`"`"|_|`"`"`"`"`"|_|`"`"`"`"`"|_|`"`"`"`"`"|_|`"`"`"`"`"|_|`"`"`"`"`"|___",
        " `"`-0-0-'`"`-0-0-'./o--000'`"`-0-0-'`"`-0-0-'`"`-0-0-'`"`-0-0-'`"`-0-0-'`"`-0-0-'`"`-0-0-'`"`-0-0-'`"`-0-0-' "
    )

    Write-Host ""
    foreach ($line in $lines) {
        Write-Host "  $line" -ForegroundColor Cyan
    }
    Write-Host ""
    Write-Host "  Bootstrapper Installer v2.0" -ForegroundColor DarkCyan
    Write-Host "  Dynamic Setup via API" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host ("  " + ("-" * 64)) -ForegroundColor DarkGray
    Write-Host ""
}


# ===========================================================================
#  CORE: Get-ApiChoices
#  Calls the real API to retrieve the list of available choice scripts.
#  Returns the parsed JSON response (status, message, data[]).
# ===========================================================================
function Get-ApiChoices {
    Show-Status -Message "Contacting API: $Script:BaseApiUrl ..." -Type "INFO"
    try {
        $response = Invoke-RestMethod -Uri $Script:BaseApiUrl -Method Get -ErrorAction Stop
        return $response
    }
    catch {
        throw "API request failed: $($_.Exception.Message)"
    }
}

# ===========================================================================
#  CORE: Fetch-AvailableChoices
#  Retrieves the list of installable choices from the API.
#  Populates $Script:AvailableChoices.
#
#  Returns: $true on success, $false on failure.
# ===========================================================================
function Fetch-AvailableChoices {
    try {
        $response = Get-ApiChoices

        if ($response.status -eq "success") {
            $Script:AvailableChoices = $response.data
            Show-Status -Message "API returned $($Script:AvailableChoices.Count) available choice(s)." -Type "SUCCESS"
            return $true
        }
        else {
            throw "API returned status: $($response.status) - $($response.message)"
        }
    }
    catch {
        Show-Status -Message "Failed to fetch choices from API." -Type "ERROR"
        Show-Status -Message "$($_.Exception.Message)" -Type "HINT"
        return $false
    }
}

# ===========================================================================
#  CORE: Invoke-InteractiveMenu
#  Multi-select menu with keyboard navigation.
#
#  Controls:
#    Up/Down   Navigate
#    Space     Toggle  [*] / [ ]
#    A         Select All
#    N         Deselect All (None)
#    Enter     Confirm
#
#  Accepts: array of choice objects (each has .name, .script, .priority)
#  Returns: array of selected choice objects
# ===========================================================================
function Invoke-InteractiveMenu {
    param(
        [Parameter(Mandatory)]
        [array]$ChoicesList,

        [Parameter(Mandatory)]
        [string]$Title
    )

    $selection = @{}
    $currentIndex = 0
    $done = $false

    # Hide cursor for clean UX
    [Console]::CursorVisible = $false

    try {
        while (-not $done) {
            # -- Draw --
            Clear-Host
            Show-Banner

            Write-Host "  $Title" -ForegroundColor White
            Write-Host ""
            Write-Host "  [Up/Down] Navigate   [Space] Toggle   [A] All   [N] None   [Enter] Confirm" -ForegroundColor DarkGray
            Write-Host ""

            for ($i = 0; $i -lt $ChoicesList.Count; $i++) {
                # Checkbox state
                $checkbox = "[ ]"
                $checkColor = "DarkGray"
                if ($selection.ContainsKey($i)) {
                    $checkbox = "[*]"
                    $checkColor = "Green"
                }

                $displayName = $ChoicesList[$i].name
                $displayPriority = $ChoicesList[$i].priority

                if ($i -eq $currentIndex) {
                    # Highlighted row
                    Write-Host "  > " -NoNewline -ForegroundColor Cyan
                    Write-Host "$checkbox " -NoNewline -ForegroundColor $checkColor -BackgroundColor DarkGray
                    Write-Host " $displayName " -NoNewline -ForegroundColor Black -BackgroundColor DarkGray
                    Write-Host " (priority: $displayPriority)" -ForegroundColor DarkGray -BackgroundColor DarkGray
                }
                else {
                    Write-Host "    $checkbox " -NoNewline -ForegroundColor $checkColor
                    Write-Host "$displayName" -NoNewline -ForegroundColor White
                    Write-Host " (priority: $displayPriority)" -ForegroundColor DarkGray
                }
            }

            # Footer: count
            $selectedCount = $selection.Count
            Write-Host ""
            Write-Host "  $selectedCount of $($ChoicesList.Count) selected" -ForegroundColor DarkGray
            Write-Host ""

            # -- Read Key --
            $key = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

            switch ($key.VirtualKeyCode) {
                38 {
                    # Up Arrow - wrap to bottom
                    if ($currentIndex -gt 0) { $currentIndex-- }
                    else { $currentIndex = $ChoicesList.Count - 1 }
                }
                40 {
                    # Down Arrow - wrap to top
                    if ($currentIndex -lt ($ChoicesList.Count - 1)) { $currentIndex++ }
                    else { $currentIndex = 0 }
                }
                32 {
                    # Space - toggle selection
                    if ($selection.ContainsKey($currentIndex)) {
                        $selection.Remove($currentIndex)
                    }
                    else {
                        $selection[$currentIndex] = $true
                    }
                }
                65 {
                    # A - Select All
                    for ($j = 0; $j -lt $ChoicesList.Count; $j++) {
                        $selection[$j] = $true
                    }
                }
                78 {
                    # N - Deselect All
                    $selection.Clear()
                }
                13 {
                    # Enter - confirm
                    $done = $true
                }
            }
        }
    }
    finally {
        [Console]::CursorVisible = $true
    }

    # Return the selected choice objects
    return $selection.Keys | Sort-Object | ForEach-Object { $ChoicesList[$_] }
}

# ===========================================================================
#  CORE: Ensure-FastDownloader
#  Ensures fast_downloader.exe is available locally.
#  Downloads from the component API if not cached.
#
#  Returns: $true if available, $false on failure.
# ===========================================================================
function Ensure-FastDownloader {
    if (Test-Path $Script:DownloaderExe) {
        Show-Status -Message "Fast Downloader found (cached)" -Type "HINT"
        return $true
    }

    Show-Status -Message "Downloading Fast Downloader component..." -Type "INFO"
    if (-not (Test-Path $Script:DownloaderDir)) {
        New-Item -ItemType Directory -Path $Script:DownloaderDir -Force | Out-Null
    }

    try {
        Invoke-WebRequest -Uri $Script:DownloaderUrl -OutFile $Script:DownloaderExe -UseBasicParsing -ErrorAction Stop
        Show-Status -Message "Fast Downloader ready" -Type "SUCCESS"
        return $true
    }
    catch {
        Show-Status -Message "Could not download Fast Downloader: $($_.Exception.Message)" -Type "ERROR"
        return $false
    }
}

# ===========================================================================
#  CORE: Get-ChoiceScript
#  Ensures a choice .ps1 is available locally in the choice folder.
#  - If the file already exists locally, it uses the cached version.
#  - If not, it downloads from the API server.
#
#  Returns: local file path, or $null on failure.
# ===========================================================================
function Get-ChoiceScript {
    param(
        [Parameter(Mandatory)][string]$FileName,
        [Parameter(Mandatory)][string]$DisplayName
    )

    $localPath = Join-Path $Script:ChoiceDir $FileName

    # Cache check — if the script already exists, skip download
    if (Test-Path $localPath) {
        Show-Status -Message "Cached: $FileName (using local copy)" -Type "HINT"
        return $localPath
    }

    # Download from real API
    $remoteUrl = "$($Script:BaseScriptUrl)/$FileName"
    Show-Status -Message "Downloading: $FileName from $remoteUrl ..." -Type "INFO"

    try {
        Invoke-WebRequest -Uri $remoteUrl -OutFile $localPath -UseBasicParsing -ErrorAction Stop

        if (-not (Test-Path $localPath)) {
            throw "File not created after download: $localPath"
        }

        Show-Status -Message "Downloaded: $FileName" -Type "SUCCESS"
        return $localPath
    }
    catch {
        Show-Status -Message "Download failed for $FileName" -Type "ERROR"
        Show-Status -Message "$($_.Exception.Message)" -Type "HINT"

        # Cleanup partial download
        if (Test-Path $localPath) {
            Remove-Item $localPath -Force -ErrorAction SilentlyContinue
        }
        return $null
    }
}

# ===========================================================================
#  CORE: Invoke-ChoiceExecution
#  Full pipeline: check cache -> download if needed -> execute the script.
#
#  Returns: PSCustomObject with Component, Priority, Status, Details
# ===========================================================================
function Invoke-ChoiceExecution {
    param(
        [Parameter(Mandatory)]
        [object]$ChoiceData
    )

    $displayName = $ChoiceData.name
    $fileName = $ChoiceData.script
    $priority = $ChoiceData.priority

    $result = [PSCustomObject]@{
        Component = $displayName
        Priority  = $priority
        Status    = "Pending"
        Details   = ""
    }

    # Step 1: Ensure script is available (cache or download)
    $scriptPath = Get-ChoiceScript -FileName $fileName -DisplayName $displayName
    if (-not $scriptPath) {
        $result.Status = "FAILED"
        $result.Details = "Download failed"
        return $result
    }

    # Step 2: Execute the choice script
    try {
        Show-Status -Message "Executing: $fileName ..." -Type "INFO"
        & $scriptPath | Out-Host

        $result.Status = "OK"
        $result.Details = "Installed successfully"
        Show-Status -Message "$displayName completed" -Type "SUCCESS"
    }
    catch {
        $result.Status = "FAILED"
        $result.Details = "$($_.Exception.Message)"
        Show-Status -Message "$displayName failed: $($_.Exception.Message)" -Type "ERROR"
    }

    return $result
}

# ===========================================================================
#                          MAIN EXECUTION
# ===========================================================================

# -- Banner --
Show-Banner

# -- Step 0: Clean and create directory structure --
# Always start fresh: remove old workspace and recreate
Show-Status -Message "Cleaning workspace: $Script:InstallerDir" -Type "INFO"

if (Test-Path $Script:InstallerDir) {
    Remove-Item -Path $Script:InstallerDir -Recurse -Force -ErrorAction SilentlyContinue
}

New-Item -ItemType Directory -Path $Script:ChoiceDir -Force | Out-Null
New-Item -ItemType Directory -Path $Script:ComponentDir -Force | Out-Null

Show-Status -Message "Workspace ready" -Type "SUCCESS"
Show-Status -Message "  choice   -> $Script:ChoiceDir" -Type "HINT"
Show-Status -Message "  component -> $Script:ComponentDir" -Type "HINT"
Write-Host ""

# -- Step 1: Fetch available choices from API --
$apiReady = Fetch-AvailableChoices
if (-not $apiReady -or $Script:AvailableChoices.Count -eq 0) {
    Show-Status -Message "No choices available from API. Exiting." -Type "ERROR"
    Write-Host ""
    exit 1
}
Write-Host ""
Start-Sleep -Milliseconds 500

# -- Step 2: Interactive Menu --
$selectedChoices = Invoke-InteractiveMenu `
    -Title "Select choice(s) to install:" `
    -ChoicesList $Script:AvailableChoices

# Validate selection
if (-not $selectedChoices -or @($selectedChoices).Count -eq 0) {
    Clear-Host
    Show-Banner
    Show-Status -Message "No choices selected. Exiting installer." -Type "ERROR"
    Write-Host ""
    exit
}

# Ensure it's always an array (single selection returns a scalar)
$selectedChoices = @($selectedChoices)

# -- Step 3: Sort by Priority & Confirm --
# Per instraction.md: execute sequence by priority (lower number = higher priority = runs first)
$sortedTasks = $selectedChoices | Sort-Object -Property { [double]$_.priority }

Clear-Host
Show-Banner
Write-Host "  Execution Queue (sorted by priority):" -ForegroundColor White
Write-Host ""
$queueNum = 0
foreach ($task in $sortedTasks) {
    $queueNum++
    Write-Host "    $queueNum. " -NoNewline -ForegroundColor White
    Write-Host "[Priority: $($task.priority)] " -NoNewline -ForegroundColor DarkYellow
    Write-Host "$($task.name)" -NoNewline -ForegroundColor Cyan
    Write-Host " -> $($task.script)" -ForegroundColor DarkGray
}
Write-Host ""
Write-Host ("  " + ("-" * 64)) -ForegroundColor DarkGray
Write-Host ""
Show-Status -Message "Starting installation of $($sortedTasks.Count) choice(s)..." -Type "INFO"
Write-Host ""
Start-Sleep -Seconds 1

# -- Step 4: Download (if needed), then Execute sequentially --
$results = @()
$sortedTasks = @($sortedTasks)
$totalSteps = if ($sortedTasks.Count -gt 0) { $sortedTasks.Count } else { 1 }
$currentStep = 0

foreach ($task in $sortedTasks) {
    $currentStep++
    $percentComplete = [math]::Round(($currentStep / $totalSteps) * 100)

    # Overall progress bar
    Write-Progress `
        -Activity "IT Support Installer" `
        -Status "[$currentStep / $totalSteps] Processing: $($task.name)" `
        -PercentComplete $percentComplete

    Write-Host ""
    Write-Host ("  " + ("-" * 64)) -ForegroundColor DarkGray
    Write-Host "  [$currentStep/$totalSteps] $($task.name) (Priority: $($task.priority))" -ForegroundColor White
    Write-Host ("  " + ("-" * 64)) -ForegroundColor DarkGray

    $installResult = Invoke-ChoiceExecution -ChoiceData $task
    $results += $installResult
}

# Close progress bar
Write-Progress -Activity "IT Support Installer" -Completed

# -- Step 5: Summary Report --
Write-Host ""
Write-Host ""
Write-Host ("  " + ("=" * 64)) -ForegroundColor DarkGray
Write-Host "  INSTALLATION SUMMARY" -ForegroundColor White
Write-Host ("  " + ("=" * 64)) -ForegroundColor DarkGray
Write-Host ""

foreach ($r in $results) {
    if ($r.Status -eq "OK") {
        $icon = "[OK]"
        $color = "Green"
        $status = "Installed"
    }
    else {
        $icon = "[!!]"
        $color = "Red"
        $status = "Failed"
    }

    Write-Host "  $icon " -NoNewline -ForegroundColor $color
    Write-Host "$($r.Component)" -NoNewline -ForegroundColor White
    Write-Host " (priority: $($r.Priority))" -NoNewline -ForegroundColor DarkGray
    Write-Host " -- $status" -ForegroundColor $color

    if ($r.Status -ne "OK" -and $r.Details) {
        Write-Host "       $($r.Details)" -ForegroundColor DarkGray
    }
}

$successCount = @($results | Where-Object { $_.Status -eq "OK" }).Count
$failCount = @($results | Where-Object { $_.Status -ne "OK" }).Count

Write-Host ""
Write-Host ("  " + ("-" * 64)) -ForegroundColor DarkGray
if ($failCount -eq 0) {
    Write-Host "  All $successCount choice(s) installed successfully!" -ForegroundColor Green
}
else {
    Write-Host "  $successCount succeeded, $failCount failed." -ForegroundColor Yellow
}
Write-Host ("  " + ("-" * 64)) -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Workspace: $Script:InstallerDir" -ForegroundColor DarkGray
Write-Host "  Thank you for using IT Support Tools!" -ForegroundColor Cyan
Write-Host ""
