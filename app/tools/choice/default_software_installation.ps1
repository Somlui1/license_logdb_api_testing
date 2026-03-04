<# 
.SYNOPSIS 
    IT Support Component: Default Software Installation (installer.7z)
.DESCRIPTION 
    Downloaded and dot-sourced by install.ps1. 
    Exposes: Install-DefaultSoftware
    
    Flow:
      1. Ensure fast_downloader.exe is available (bootstrap via API if missing)
      2. Download installer.7z from FTPS server using fast_downloader.exe
      3. Detect 7-Zip on the local machine
      4. If 7-Zip not found -> download 7z installer via FTPS and install silently
      5. Extract installer.7z to component directory
      6. Run the start script (start_process.cmd) inside the extracted folder

.NOTES
    Author : IT Support DevOps Team
    Version: 1.0.0
#> 

# ===========================================================================
#  CONFIGURATION  (Edit these values as needed)
# ===========================================================================

# --- FTP Server ---
$Script:FtpInstallerUrl = "ftp://itsupport@10.10.3.215/program.7z"
$Script:FtpUsername = "itsupport"                                      # FTP username
$Script:FtpPassword = "aapico"                                        # FTP password

# --- 7-Zip Auto-Install ---
$Script:Ftp7ZipUrl = "ftp://itsupport@10.10.3.215/7z2600-x64.exe"
$Script:7ZipInstallerFile = "7z2600-x64.exe"

# --- Component File ---
$Script:ComponentFile = "program.7z"
$Script:ExtractFolderName = "program"                                      # Folder name after extraction

# --- Start Script (relative path inside extracted folder) ---
$Script:StartScriptName = "program/launcher.ps1"

# --- Directories (inherited from install.ps1 folder structure) ---
$Script:InstallerDir = Join-Path $env:TEMP "itsupport_tools"
$Script:ComponentDir = Join-Path $Script:InstallerDir "component"
$Script:ToolsDir = Join-Path $Script:InstallerDir "tools"
$Script:DownloaderExe = Join-Path $Script:ToolsDir "fast_downloader.exe"
$Script:DownloaderThreads = 8
#C:\Users\wajeepradit.p\git\installer\program\launcher.ps1
# --- API Server (for fast_downloader.exe bootstrap) ---
$Script:ComponentDownloadUrl = "http://localhost:8000/tools/cli-tools/component/download"
$Script:DownloaderUrl = "$Script:ComponentDownloadUrl/fast_downloader.exe"

# ===========================================================================
#  MAIN FUNCTION
# ===========================================================================

function Install-DefaultSoftware {
    <#
    .SYNOPSIS
        Downloads program.7z via FTPS, extracts with 7-Zip (auto-install if missing),
        and runs the start script inside.
    #>

    Write-Host ""
    Write-Host "  ================================================================" -ForegroundColor DarkGray
    Write-Host "  Default Software Installation (program.7z)" -ForegroundColor Cyan
    Write-Host "  ================================================================" -ForegroundColor DarkGray
    Write-Host ""

    # Ensure component directory exists
    if (-not (Test-Path $Script:ComponentDir)) {
        New-Item -ItemType Directory -Path $Script:ComponentDir -Force | Out-Null
    }

    $archivePath = Join-Path $Script:ComponentDir $Script:ComponentFile

    # ------------------------------------------------------------------
    #  Pre-check: Skip download steps if installer.7z already exists
    # ------------------------------------------------------------------
    if (Test-Path $archivePath) {
        Write-Host "  [Step 1/6] Skipped — $($Script:ComponentFile) already exists" -ForegroundColor DarkGray
        Write-Host "  [Step 2/6] Skipped — using cached file: $archivePath" -ForegroundColor DarkGray
    }
    else {
        # ------------------------------------------------------------------
        #  Step 1: Ensure fast_downloader.exe is available
        # ------------------------------------------------------------------
        Write-Host "  [Step 1/6] Checking fast_downloader.exe ..." -ForegroundColor Yellow

        if (Test-Path $Script:DownloaderExe) {
            Write-Host "     fast_downloader.exe found (cached)" -ForegroundColor DarkGray
        }
        else {
            # Create tools directory
            if (-not (Test-Path $Script:ToolsDir)) {
                New-Item -ItemType Directory -Path $Script:ToolsDir -Force | Out-Null
            }

            # Check curl.exe availability (ships with Windows 10+)
            if (-not (Get-Command "curl.exe" -ErrorAction SilentlyContinue)) {
                throw "curl.exe not found on this system. Cannot bootstrap fast_downloader.exe."
            }

            Write-Host "     Downloading fast_downloader.exe via curl ..." -ForegroundColor Gray

            try {
                & curl.exe -L --fail -# -o "$($Script:DownloaderExe)" "$($Script:DownloaderUrl)"

                if ($LASTEXITCODE -ne 0) {
                    throw "curl exited with code $LASTEXITCODE"
                }

                if (-not (Test-Path $Script:DownloaderExe)) {
                    throw "File not created after download"
                }

                Write-Host "     [OK] fast_downloader.exe ready" -ForegroundColor Green
            }
            catch {
                # Cleanup partial download
                if (Test-Path $Script:DownloaderExe) {
                    Remove-Item $Script:DownloaderExe -Force -ErrorAction SilentlyContinue
                }
                throw "Failed to download fast_downloader.exe: $($_.Exception.Message)"
            }
        }

        # ------------------------------------------------------------------
        #  Step 2: Download installer.7z from FTPS server
        # ------------------------------------------------------------------
        Write-Host ""
        Write-Host "  [Step 2/6] Downloading $($Script:ComponentFile) via FTPS ..." -ForegroundColor Yellow

        try {
            # fast_downloader.exe auto-negotiates FTPS/TLS for ftp:// URLs
            # CLI: fast_downloader.exe <URL> -u <username> -p <password> -o <filename> -d <directory>
            # Use Start-Process -NoNewWindow so the exe inherits the real console
            # and its Rich progress bar renders correctly in the terminal.
            $dlArgs = @(
                $Script:FtpInstallerUrl,
                "-u", $Script:FtpUsername,
                "-p", $Script:FtpPassword,
                "-o", $Script:ComponentFile,
                "-d", $Script:ComponentDir
            )
            $dlProc = Start-Process -FilePath $Script:DownloaderExe `
                -ArgumentList $dlArgs `
                -NoNewWindow -Wait -PassThru

            if ($dlProc.ExitCode -ne 0) {
                throw "fast_downloader.exe exited with code $($dlProc.ExitCode)"
            }

            if (-not (Test-Path $archivePath)) {
                throw "File not found after download: $archivePath"
            }

            Write-Host "     [OK] Downloaded $($Script:ComponentFile)" -ForegroundColor Green
        }
        catch {
            # Cleanup partial download
            if (Test-Path $archivePath) {
                Remove-Item $archivePath -Force -ErrorAction SilentlyContinue
            }
            throw "Failed to download $($Script:ComponentFile): $($_.Exception.Message)"
        }
    }

    # ------------------------------------------------------------------
    #  Step 3: Detect 7-Zip
    # ------------------------------------------------------------------
    Write-Host ""
    Write-Host "  [Step 3/6] Checking 7-Zip installation ..." -ForegroundColor Yellow

    $7zPath = $null

    # Try PATH first
    $7zCmd = Get-Command "7z" -ErrorAction SilentlyContinue
    if ($7zCmd) {
        $7zPath = "7z"
    }
    # Try standard installation paths
    elseif (Test-Path "C:\Program Files\7-Zip\7z.exe") {
        $7zPath = "C:\Program Files\7-Zip\7z.exe"
    }
    elseif (Test-Path "C:\Program Files (x86)\7-Zip\7z.exe") {
        $7zPath = "C:\Program Files (x86)\7-Zip\7z.exe"
    }

    if ($7zPath) {
        Write-Host "     [OK] 7-Zip found at: $7zPath" -ForegroundColor Green
    }
    else {
        # ------------------------------------------------------------------
        #  Step 4: Auto-install 7-Zip from FTPS server
        # ------------------------------------------------------------------
        Write-Host "     7-Zip not found. Downloading installer from FTPS ..." -ForegroundColor Yellow

        $7zInstallerPath = Join-Path $Script:ComponentDir $Script:7ZipInstallerFile

        try {
            # Download 7-Zip installer via FTPS using fast_downloader.exe
            # Use Start-Process -NoNewWindow so progress bar renders in terminal
            $dl7zArgs = @(
                $Script:Ftp7ZipUrl,
                "-u", $Script:FtpUsername,
                "-p", $Script:FtpPassword,
                "-o", $Script:7ZipInstallerFile,
                "-d", $Script:ComponentDir
            )
            $dl7zProc = Start-Process -FilePath $Script:DownloaderExe `
                -ArgumentList $dl7zArgs `
                -NoNewWindow -Wait -PassThru

            if ($dl7zProc.ExitCode -ne 0) {
                throw "fast_downloader.exe exited with code $($dl7zProc.ExitCode)"
            }

            if (-not (Test-Path $7zInstallerPath)) {
                throw "7-Zip installer not found after download: $7zInstallerPath"
            }

            Write-Host "     [OK] Downloaded $($Script:7ZipInstallerFile)" -ForegroundColor Green
        }
        catch {
            if (Test-Path $7zInstallerPath) {
                Remove-Item $7zInstallerPath -Force -ErrorAction SilentlyContinue
            }
            throw "Failed to download 7-Zip installer: $($_.Exception.Message)"
        }

        # Run 7-Zip silent install  (/S = silent mode for NSIS-based installer)
        Write-Host "     Installing 7-Zip silently ..." -ForegroundColor Gray

        try {
            $process = Start-Process -FilePath $7zInstallerPath `
                -ArgumentList "/S" `
                -Wait -PassThru -NoNewWindow

            if ($process.ExitCode -ne 0) {
                throw "7-Zip installer exited with code $($process.ExitCode)"
            }

            # Verify installation
            if (Test-Path "C:\Program Files\7-Zip\7z.exe") {
                $7zPath = "C:\Program Files\7-Zip\7z.exe"
            }
            elseif (Test-Path "C:\Program Files (x86)\7-Zip\7z.exe") {
                $7zPath = "C:\Program Files (x86)\7-Zip\7z.exe"
            }
            else {
                throw "7-Zip installation completed but 7z.exe not found in expected paths."
            }

            Write-Host "     [OK] 7-Zip installed at: $7zPath" -ForegroundColor Green
        }
        catch {
            throw "Failed to install 7-Zip: $($_.Exception.Message)"
        }

        # Cleanup installer
        Remove-Item $7zInstallerPath -Force -ErrorAction SilentlyContinue
    }

    # ------------------------------------------------------------------
    #  Step 5: Extract installer.7z to component directory
    # ------------------------------------------------------------------
    Write-Host ""
    Write-Host "  [Step 5/6] Extracting $($Script:ComponentFile) ..." -ForegroundColor Yellow

    $extractDir = Join-Path $Script:ComponentDir $Script:ExtractFolderName

    # Clean previous extraction if exists
    if (Test-Path $extractDir) {
        Write-Host "     Removing previous extraction ..." -ForegroundColor DarkGray
        Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue
    }

    # Create the extraction subfolder: component/{zipfilename}/
    New-Item -ItemType Directory -Path $extractDir -Force | Out-Null

    try {
        # 7z x = extract with full paths, -o = output dir (into subfolder), -y = auto-yes
        & $7zPath x "$archivePath" -o"$extractDir" -y

        if ($LASTEXITCODE -ne 0) {
            throw "7-Zip extraction exited with code $LASTEXITCODE"
        }

        if (-not (Test-Path $extractDir)) {
            throw "Extracted folder not found: $extractDir"
        }

        Write-Host "     [OK] Extraction complete -> $extractDir" -ForegroundColor Green
    }
    catch {
        throw "Failed to extract $($Script:ComponentFile): $($_.Exception.Message)"
    }

    # ------------------------------------------------------------------
    #  Step 6: Run main.ps1 installation script
    # ------------------------------------------------------------------
    Write-Host ""
    Write-Host "  [Step 6/6] Running main.ps1 installation script ..." -ForegroundColor Yellow

    $startScript = Join-Path $extractDir $Script:StartScriptName

    if (-not (Test-Path $startScript)) {
        throw "Start script not found: $startScript"
    }

    try {
        # Set working directory to the script's folder so $PSScriptRoot resolves correctly
        $scriptWorkingDir = Split-Path -Parent $startScript
        Write-Host "     Executing: $startScript" -ForegroundColor Gray
        Write-Host "     Working Dir: $scriptWorkingDir" -ForegroundColor DarkGray

        $process = Start-Process -FilePath "powershell.exe" `
            -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$startScript`"" `
            -WorkingDirectory $scriptWorkingDir `
            -Wait -PassThru -NoNewWindow

        if ($process.ExitCode -ne 0) {
            Write-Host "     [WARNING] main.ps1 exited with code $($process.ExitCode)" -ForegroundColor Yellow
        }
        else {
            Write-Host "     [OK] main.ps1 completed successfully" -ForegroundColor Green
        }
    }
    catch {
        throw "Failed to run main.ps1: $($_.Exception.Message)"
    }

    # ------------------------------------------------------------------
    #  Done
    # ------------------------------------------------------------------
    Write-Host ""
    Write-Host "  ================================================================" -ForegroundColor DarkGray
    Write-Host "  [OK] Default Software Installation completed!" -ForegroundColor Green
    Write-Host "  ================================================================" -ForegroundColor DarkGray
    Write-Host ""
}

# ===========================================================================
#  AUTO-EXECUTE when dot-sourced by install.ps1
# ===========================================================================
Install-DefaultSoftware
