
$Script:BaseApiUrl = "http://10.10.3.215:8181/tools/cli-tools/choice"
$Script:BaseScriptUrl = "http://10.10.3.215:8181/tools/cli-tools/choice/download"
$Script:ComponentApiUrl = "http://10.10.3.215:8181/tools/cli-tools/component"
$Script:ComponentDownloadUrl = "http://10.10.3.215:8181/tools/cli-tools/component/download"

$Script:InstallerDir = Join-Path $env:TEMP "itsupport_tools"
$Script:ChoiceDir = Join-Path $Script:InstallerDir "choice"
$Script:ComponentDir = Join-Path $Script:InstallerDir "component"

$Script:DownloaderUrl = "$Script:ComponentDownloadUrl/fast_downloader.exe"
$Script:DownloaderDir = Join-Path $Script:InstallerDir "tools"
$Script:DownloaderExe = Join-Path $Script:DownloaderDir "fast_downloader.exe"
$Script:DownloaderThreads = 8

$Script:AvailableChoices = @()


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

function Show-Banner {
    Clear-Host
  
    $lines = @(
        '                                                                                                    ',
        '88  888888888888     ad88888ba   88        88  88888888ba   88888888ba     ,ad8888ba,    88888888ba  888888888888  ',
        '88       88          d8"     "8b  88        88  88      "8b  88      "8b   d8"''    `"8b   88      "8b      88        ',
        '88       88          Y8,          88        88  88      ,8P  88      ,8P  d8''        `8b  88      ,8P      88        ',
        '88       88          `Y8aaaaa,    88        88  88aaaaaa8P''  88aaaaaa8P''  88          88  88aaaaaa8P''      88        ',
        '88       88            `"""""8b,  88        88  88""""""''    88""""""''    88          88  88""""88''        88        ',
        '88       88                  `8b  88        88  88           88           Y8,        ,8P  88    `8b        88        ',
        '88       88          Y8a     a8P  Y8a.    .a8P  88           88            Y8a.    .a8P   88     `8b       88        ',
        '88       88           "Y88888P"    `"Y8888Y"''   88           88             `"Y8888Y"''    88      `8b      88        ',
        '                                                                                                    '
    )

    foreach ($line in $lines) {
        Write-Host "  $line" -ForegroundColor blue
    }
    Write-Host ""
    Write-Host "  Bootstrapper Installer v2.0" -ForegroundColor DarkCyan
    Write-Host "  Dynamic Setup via API" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host ("  " + ("-" * 64)) -ForegroundColor DarkGray
    Write-Host ""
}



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


    [Console]::CursorVisible = $false

    try {
        while (-not $done) {
        
            Clear-Host
            Show-Banner

            Write-Host "  $Title" -ForegroundColor White
            Write-Host ""
            Write-Host "  [Up/Down] Navigate   [Space] Toggle   [A] All   [N] None   [Enter] Confirm" -ForegroundColor DarkGray
            Write-Host ""

            for ($i = 0; $i -lt $ChoicesList.Count; $i++) {
                
                $checkbox = "[ ]"
                $checkColor = "DarkGray"
                if ($selection.ContainsKey($i)) {
                    $checkbox = "[*]"
                    $checkColor = "Green"
                }

                $displayName = $ChoicesList[$i].name
                $displayPriority = $ChoicesList[$i].priority

                if ($i -eq $currentIndex) {
                    
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

            
            $selectedCount = $selection.Count
            Write-Host ""
            Write-Host "  $selectedCount of $($ChoicesList.Count) selected" -ForegroundColor DarkGray
            Write-Host ""

            
            $key = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

            switch ($key.VirtualKeyCode) {
                38 {
                    
                    if ($currentIndex -gt 0) { $currentIndex-- }
                    else { $currentIndex = $ChoicesList.Count - 1 }
                }
                40 {
                    
                    if ($currentIndex -lt ($ChoicesList.Count - 1)) { $currentIndex++ }
                    else { $currentIndex = 0 }
                }
                32 {
                    
                    if ($selection.ContainsKey($currentIndex)) {
                        $selection.Remove($currentIndex)
                    }
                    else {
                        $selection[$currentIndex] = $true
                    }
                }
                65 {
                    
                    for ($j = 0; $j -lt $ChoicesList.Count; $j++) {
                        $selection[$j] = $true
                    }
                }
                78 {
                    
                    $selection.Clear()
                }
                13 {
                    
                    $done = $true
                }
            }
        }
    }
    finally {
        [Console]::CursorVisible = $true
    }

    
    return $selection.Keys | Sort-Object | ForEach-Object { $ChoicesList[$_] }
}








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









function Get-ChoiceScript {
    param(
        [Parameter(Mandatory)][string]$FileName,
        [Parameter(Mandatory)][string]$DisplayName
    )

    $localPath = Join-Path $Script:ChoiceDir $FileName

    
    if (Test-Path $localPath) {
        Show-Status -Message "Cached: $FileName (using local copy)" -Type "HINT"
        return $localPath
    }

    
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

        
        if (Test-Path $localPath) {
            Remove-Item $localPath -Force -ErrorAction SilentlyContinue
        }
        return $null
    }
}







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

    
    $scriptPath = Get-ChoiceScript -FileName $fileName -DisplayName $displayName
    if (-not $scriptPath) {
        $result.Status = "FAILED"
        $result.Details = "Download failed"
        return $result
    }

    
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



set-executionpolicy -ExecutionPolicy Bypass -Scope Process

Show-Banner



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


$apiReady = Fetch-AvailableChoices
if (-not $apiReady -or $Script:AvailableChoices.Count -eq 0) {
    Show-Status -Message "No choices available from API. Exiting." -Type "ERROR"
    Write-Host ""
    exit 1
}
Write-Host ""
Start-Sleep -Milliseconds 500


$selectedChoices = Invoke-InteractiveMenu `
    -Title "Select choice(s) to install:" `
    -ChoicesList $Script:AvailableChoices


if (-not $selectedChoices -or @($selectedChoices).Count -eq 0) {
    Clear-Host
    Show-Banner
    Show-Status -Message "No choices selected. Exiting installer." -Type "ERROR"
    Write-Host ""
    exit
}


$selectedChoices = @($selectedChoices)



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


$results = @()
$sortedTasks = @($sortedTasks)
$totalSteps = if ($sortedTasks.Count -gt 0) { $sortedTasks.Count } else { 1 }
$currentStep = 0

foreach ($task in $sortedTasks) {
    $currentStep++
    $percentComplete = [math]::Round(($currentStep / $totalSteps) * 100)

    
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


Write-Progress -Activity "IT Support Installer" -Completed


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
