# MetaName: WiFi Ticket Generator
# MetaPriority: 5.0
<#
.SYNOPSIS
    OpenClaw Component: WiFi Ticket Generator
.DESCRIPTION
    Downloaded and dot-sourced by install.ps1.
    Exposes: Install-TicketGenerator

    Dynamic interactive CLI that:
      1. Fetches Network Groups from API  (GET /SOS/wifi/groups)
      2. Fetches WiFi Profiles for selected group (GET /SOS/wifi/groups/{name}/profiles)
      3. Collects quantity input
      4. Opens browser to generate tickets
#>

# ===========================================================================
#  CONFIGURATION
# ===========================================================================
$Script:ApiBaseUrl = "http://10.10.3.215:8181"
$Script:GroupsApi = "$($Script:ApiBaseUrl)/SOS/wifi/groups"
$Script:TicketApiBase = "$($Script:ApiBaseUrl)/SOS/generate-ticket/print"

# ===========================================================================
#  HELPER: Show-TicketBanner
# ===========================================================================
function Show-TicketBanner {
    Clear-Host
    Write-Host ""
    Write-Host "       ___       ___       ___       ___   " -ForegroundColor DarkCyan
    Write-Host "      |\  \     |\  \     |\  \     |\  \  " -ForegroundColor DarkCyan
    Write-Host "      \ \  \    \ \  \    \ \  \    \ \  \ " -ForegroundColor Cyan
    Write-Host "       \ \  \    \ \  \    \ \  \    \ \  \" -ForegroundColor Cyan
    Write-Host "        \ \  \____\ \  \____\ \  \____\ \  \" -ForegroundColor DarkCyan
    Write-Host "         \ \_______\ \_______\ \_______\ \__\" -ForegroundColor DarkCyan
    Write-Host "          \|_______|\|_______|\|_______|\|__|" -ForegroundColor DarkGray
    Write-Host ""
    $bar = ''.PadRight(54, [char]0x2550)
    $vl = [char]0x2551
    Write-Host ('  {0}' -f [char]0x2554) -NoNewline -ForegroundColor DarkCyan
    Write-Host $bar -NoNewline -ForegroundColor DarkCyan
    Write-Host ([char]0x2557) -ForegroundColor DarkCyan
    Write-Host "  $vl" -NoNewline -ForegroundColor DarkCyan
    Write-Host (''.PadRight(54)) -NoNewline
    Write-Host "$vl" -ForegroundColor DarkCyan
    Write-Host "  $vl   " -NoNewline -ForegroundColor DarkCyan
    Write-Host 'W I F I   T I C K E T   G E N E R A T O R' -NoNewline -ForegroundColor White
    Write-Host "   $vl" -ForegroundColor DarkCyan
    Write-Host "  $vl" -NoNewline -ForegroundColor DarkCyan
    Write-Host (''.PadRight(54)) -NoNewline
    Write-Host "$vl" -ForegroundColor DarkCyan
    Write-Host "  $vl   " -NoNewline -ForegroundColor DarkCyan
    Write-Host 'Generate guest WiFi access tickets via API' -NoNewline -ForegroundColor DarkGray
    Write-Host "    $vl" -ForegroundColor DarkCyan
    Write-Host "  $vl" -NoNewline -ForegroundColor DarkCyan
    Write-Host (''.PadRight(54)) -NoNewline
    Write-Host "$vl" -ForegroundColor DarkCyan
    Write-Host ('  {0}' -f [char]0x255A) -NoNewline -ForegroundColor DarkCyan
    Write-Host $bar -NoNewline -ForegroundColor DarkCyan
    Write-Host ([char]0x255D) -ForegroundColor DarkCyan
    Write-Host ""
}

# ===========================================================================
#  HELPER: Invoke-MenuSelector
#  Generic arrow-key interactive selector
#  Accepts: array of display strings, title
#  Returns: selected index
# ===========================================================================
function Invoke-MenuSelector {
    param(
        [Parameter(Mandatory)][string[]]$Items,
        [Parameter(Mandatory)][string]$Title
    )

    $currentIndex = 0
    $done = $false

    [Console]::CursorVisible = $false

    try {
        while (-not $done) {
            $startY = [Console]::CursorTop

            Write-Host ""
            Write-Host "  $Title" -ForegroundColor White
            Write-Host ""
            Write-Host '  (Up/Down) Navigate   (Enter) Confirm' -ForegroundColor DarkGray
            Write-Host ""

            for ($i = 0; $i -lt $Items.Count; $i++) {
                if ($i -eq $currentIndex) {
                    Write-Host "    > " -NoNewline -ForegroundColor Cyan
                    Write-Host '(*) ' -NoNewline -ForegroundColor Green
                    Write-Host "$($Items[$i])" -ForegroundColor White -BackgroundColor DarkGray
                }
                else {
                    Write-Host "      " -NoNewline
                    Write-Host '( ) ' -NoNewline -ForegroundColor DarkGray
                    Write-Host "$($Items[$i])" -ForegroundColor Gray
                }
            }

            Write-Host ""
            Write-Host "  $($currentIndex + 1) of $($Items.Count)" -ForegroundColor DarkGray
            Write-Host ""

            $key = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

            switch ($key.VirtualKeyCode) {
                38 {
                    # Up
                    if ($currentIndex -gt 0) { $currentIndex-- }
                    else { $currentIndex = $Items.Count - 1 }
                }
                40 {
                    # Down
                    if ($currentIndex -lt ($Items.Count - 1)) { $currentIndex++ }
                    else { $currentIndex = 0 }
                }
                13 {
                    # Enter
                    $done = $true
                }
            }

            if (-not $done) {
                $endY = [Console]::CursorTop
                $linesToClear = $endY - $startY
                [Console]::SetCursorPosition(0, $startY)
                for ($j = 0; $j -lt $linesToClear; $j++) {
                    Write-Host (" " * [Console]::WindowWidth)
                }
                [Console]::SetCursorPosition(0, $startY)
            }
        }
    }
    finally {
        [Console]::CursorVisible = $true
    }

    return $currentIndex
}

# ===========================================================================
#  API: Get-WifiGroups
#  Fetches all network groups from: GET /SOS/wifi/groups
#  Returns: array of group objects [{name, groupId}]
# ===========================================================================
function Get-WifiGroups {
    Write-Host "  Fetching network groups from API ..." -ForegroundColor Gray
    Write-Host "  GET $Script:GroupsApi" -ForegroundColor DarkGray

    try {
        $response = Invoke-RestMethod -Uri $Script:GroupsApi -Method Get -ErrorAction Stop -TimeoutSec 15
        return $response
    }
    catch {
        throw "Failed to fetch groups: $($_.Exception.Message)"
    }
}

# ===========================================================================
#  API: Get-WifiProfiles
#  Fetches profiles for a group: GET /SOS/wifi/groups/{groupname}/profiles
#  Returns: array of profile objects [{name, id, authProfileId, ...}]
# ===========================================================================
function Get-WifiProfiles {
    param(
        [Parameter(Mandatory)][string]$GroupName
    )

    $profileUrl = "$Script:GroupsApi/$GroupName/profiles"
    Write-Host "  Fetching profiles for '$GroupName' ..." -ForegroundColor Gray
    Write-Host "  GET $profileUrl" -ForegroundColor DarkGray

    try {
        $response = Invoke-RestMethod -Uri $profileUrl -Method Get -ErrorAction Stop -TimeoutSec 15
        return $response
    }
    catch {
        throw "Failed to fetch profiles for '$GroupName': $($_.Exception.Message)"
    }
}

# ===========================================================================
#  MAIN: Install-TicketGenerator
# ===========================================================================
function Install-TicketGenerator {
    <#
    .SYNOPSIS
        Dynamic WiFi ticket generator - fetches groups/profiles from API,
        collects input, and opens browser to generate tickets.
    #>

    Show-TicketBanner

    # ==================================================================
    #  Step 1/3: Select Network Group (from API)
    # ==================================================================
    Write-Host "  +---------------------------------------------------------+" -ForegroundColor DarkGray
    Write-Host '  |  STEP 1/3  Select Network Group (Company)             |' -ForegroundColor DarkGray
    Write-Host "  +---------------------------------------------------------+" -ForegroundColor DarkGray
    Write-Host ""

    # Fetch groups from API
    $groups = $null
    try {
        $groups = Get-WifiGroups

        # Handle different response structures
        if ($groups.data) { $groups = $groups.data }
        $groups = @($groups)

        if ($groups.Count -eq 0) {
            throw "API returned 0 groups."
        }

        Write-Host "  (OK) Found $($groups.Count) group(s)" -ForegroundColor Green
    }
    catch {
        Write-Host ""
        Write-Host "  (!) Error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "  Please check that the API server is running at: $Script:ApiBaseUrl" -ForegroundColor Yellow
        Write-Host ""
        return
    }

    # Build display items for selector
    $groupDisplayItems = @()
    foreach ($g in $groups) {
        $gName = if ($g.name) { $g.name } else { "$g" }
        $gId = if ($g.groupId) { " (ID: $($g.groupId))" } else { "" }
        $groupDisplayItems += "$gName$gId"
    }

    # Interactive menu to select group
    $selectedGroupIndex = Invoke-MenuSelector -Items $groupDisplayItems -Title "Select Network Group:"
    $selectedGroup = $groups[$selectedGroupIndex]
    $groupname = if ($selectedGroup.name) { $selectedGroup.name } else { "$selectedGroup" }

    Write-Host "  (OK) Group: $groupname" -ForegroundColor Green
    Write-Host ""

    # ==================================================================
    #  Step 2/3: Select WiFi Profile (from API, based on group)
    # ==================================================================
    Write-Host "  +---------------------------------------------------------+" -ForegroundColor DarkGray
    Write-Host '  |  STEP 2/3  Select WiFi Profile                        |' -ForegroundColor DarkGray
    Write-Host "  +---------------------------------------------------------+" -ForegroundColor DarkGray
    Write-Host ""

    # Fetch profiles from API for the selected group
    $profiles = $null
    try {
        $profiles = Get-WifiProfiles -GroupName $groupname

        # Handle different response structures
        if ($profiles.data) { $profiles = $profiles.data }
        $profiles = @($profiles)

        if ($profiles.Count -eq 0) {
            throw "No profiles found for group '$groupname'."
        }

        Write-Host "  (OK) Found $($profiles.Count) profile(s) for '$groupname'" -ForegroundColor Green
    }
    catch {
        Write-Host ""
        Write-Host "  (!) Error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "  This group may not have any WiFi profiles configured." -ForegroundColor Yellow
        Write-Host ""
        return
    }

    # Build display items for selector with profile details
    $profileDisplayItems = @()
    foreach ($p in $profiles) {
        $pName = if ($p.name) { $p.name } else { "$p" }
        $pPeriod = if ($p.period) { " | Period: $($p.period)" } else { "" }
        $pRate = if ($p.maximum_download_rate) { " | Speed: $($p.maximum_download_rate)" } else { "" }
        $profileDisplayItems += "$pName$pPeriod$pRate"
    }

    # Interactive menu to select profile
    $selectedProfileIndex = Invoke-MenuSelector -Items $profileDisplayItems -Title "Select WiFi Profile for '$groupname':"
    $selectedProfile = $profiles[$selectedProfileIndex]
    $profile_name = if ($selectedProfile.name) { $selectedProfile.name } else { "$selectedProfile" }

    Write-Host "  (OK) Profile: $profile_name" -ForegroundColor Green
    Write-Host ""

    # ==================================================================
    #  Step 3/3: Quantity
    # ==================================================================
    Write-Host "  +---------------------------------------------------------+" -ForegroundColor DarkGray
    Write-Host '  |  STEP 3/3  Ticket Quantity                            |' -ForegroundColor DarkGray
    Write-Host "  +---------------------------------------------------------+" -ForegroundColor DarkGray
    Write-Host ""

    $quantity = 0
    do {
        Write-Host "  Quantity: " -NoNewline -ForegroundColor Cyan
        $input_qty = Read-Host

        if ($input_qty -match '^\d+$' -and [int]$input_qty -gt 0) {
            $quantity = [int]$input_qty
        }
        else {
            Write-Host '  (!) Please enter a valid number greater than 0.' -ForegroundColor Red
            Write-Host ""
        }
    } while ($quantity -le 0)

    Write-Host ""
    Write-Host "  (OK) Quantity: $quantity" -ForegroundColor Green
    Write-Host ""

    # ==================================================================
    #  Confirmation Summary
    # ==================================================================
    $bar = ''.PadRight(54, [char]0x2550)
    $vl = [char]0x2551

    Write-Host "  $([char]0x2554)$bar$([char]0x2557)" -ForegroundColor DarkCyan
    Write-Host "  $vl  " -NoNewline -ForegroundColor DarkCyan
    Write-Host 'TICKET SUMMARY' -NoNewline -ForegroundColor White
    Write-Host "                                    $vl" -ForegroundColor DarkCyan
    Write-Host "  $([char]0x2560)$bar$([char]0x2563)" -ForegroundColor DarkCyan
    Write-Host "  $vl                                                      $vl" -ForegroundColor DarkCyan

    # Group row
    Write-Host "  $vl  " -NoNewline -ForegroundColor DarkCyan
    Write-Host "  Group   :  " -NoNewline -ForegroundColor Gray
    $padded1 = $groupname.PadRight(36)
    Write-Host "$padded1" -NoNewline -ForegroundColor White
    Write-Host "  $vl" -ForegroundColor DarkCyan

    # Profile row
    Write-Host "  $vl  " -NoNewline -ForegroundColor DarkCyan
    Write-Host "  Profile :  " -NoNewline -ForegroundColor Gray
    $padded2 = $profile_name.PadRight(36)
    Write-Host "$padded2" -NoNewline -ForegroundColor White
    Write-Host "  $vl" -ForegroundColor DarkCyan

    # Quantity row
    Write-Host "  $vl  " -NoNewline -ForegroundColor DarkCyan
    Write-Host "  Quantity:  " -NoNewline -ForegroundColor Gray
    $padded3 = "$quantity ticket(s)".PadRight(36)
    Write-Host "$padded3" -NoNewline -ForegroundColor White
    Write-Host "  $vl" -ForegroundColor DarkCyan

    Write-Host "  $vl                                                      $vl" -ForegroundColor DarkCyan
    Write-Host "  $([char]0x255A)$bar$([char]0x255D)" -ForegroundColor DarkCyan
    Write-Host ""

    Write-Host "  Proceed and open browser? (Y/N): " -NoNewline -ForegroundColor Yellow
    $confirm = Read-Host

    if ($confirm -notmatch '^[Yy]') {
        Write-Host ""
        Write-Host '  (!) Cancelled by user.' -ForegroundColor Yellow
        Write-Host ""
        return
    }

    # ==================================================================
    #  Build URL & Launch Browser
    # ==================================================================
    $encodedGroup = [System.Uri]::EscapeDataString($groupname)
    $encodedProfile = [System.Uri]::EscapeDataString($profile_name)

    $url = "$($Script:TicketApiBase)?groupname=$encodedGroup&profile_name=$encodedProfile&quantity=$quantity"

    Write-Host ""
    Write-Host "  +---------------------------------------------------------+" -ForegroundColor DarkGray
    Write-Host '  |  Opening browser ...                                     |' -ForegroundColor DarkGray
    Write-Host "  +---------------------------------------------------------+" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  URL: " -NoNewline -ForegroundColor Gray
    Write-Host "$url" -ForegroundColor Cyan
    Write-Host ""

    try {
        Start-Process msedge "$url"
        Write-Host '  (OK) Browser launched successfully!' -ForegroundColor Green
    }
    catch {
        Write-Host "  (FAIL) Could not open browser: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host '  Please open the URL manually.' -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "  ================================================================" -ForegroundColor DarkGray
    Write-Host "  Thank you for using WiFi Ticket Generator!" -ForegroundColor Cyan
    Write-Host "  ================================================================" -ForegroundColor DarkGray
    Write-Host ""
}

Install-TicketGenerator