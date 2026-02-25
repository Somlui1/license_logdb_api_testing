# ==========================================
# MOCKUP INSTALLER - UX DEMO ONLY
# ==========================================

# 1. Helper Function: สร้างเมนูแบบ Interactive (เลือกด้วย Space Bar)
function Invoke-InteractiveMenu {
    param([string[]]$Options, [string]$Title)
    
    $selection = @{}
    $currentIndex = 0
    $done = $false
    
    # ซ่อน Cursor เพื่อความสวยงาม
    [Console]::CursorVisible = $false

    try {
        while (-not $done) {
            # วาดหน้าจอเมนู
            Clear-Host
            Write-Host "`n $Title" -ForegroundColor Cyan
            Write-Host " [Use Arrow Keys to move, SPACE to select, ENTER to confirm]`n" -ForegroundColor Gray

            for ($i = 0; $i -lt $Options.Count; $i++) {
                $prefix = "[ ]"
                if ($selection.ContainsKey($i)) { $prefix = "[*]" }
                
                # Highlight บรรทัดที่เลือกอยู่
                if ($i -eq $currentIndex) {
                    Write-Host " > $prefix $($Options[$i])" -ForegroundColor Black -BackgroundColor Cyan
                }
                else {
                    Write-Host "   $prefix $($Options[$i])" -ForegroundColor White
                }
            }

            # รอรับปุ่มกด
            $key = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
            
            switch ($key.VirtualKeyCode) {
                38 {
                    # Up Arrow
                    if ($currentIndex -gt 0) { $currentIndex-- }
                }
                40 {
                    # Down Arrow
                    if ($currentIndex -lt ($Options.Count - 1)) { $currentIndex++ }
                }
                32 {
                    # Space Bar
                    if ($selection.ContainsKey($currentIndex)) {
                        $selection.Remove($currentIndex)
                    }
                    else {
                        $selection[$currentIndex] = $true
                    }
                }
                13 {
                    # Enter
                    $done = $true
                }
            }
        }
    }
    finally {
        [Console]::CursorVisible = $true
    }

    # คืนค่ารายการที่เลือกกลับไป
    return $selection.Keys | Sort-Object | ForEach-Object { $Options[$_] }
}

# 2. Helper Function: จำลองการแสดงสถานะ (Status Indicators)
function Show-Status {
    param([string]$Message, [string]$Type)
    
    switch ($Type) {
        "INFO" { Write-Host "[*] $Message" -ForegroundColor Yellow }
        "SUCCESS" { Write-Host "[OK] $Message" -ForegroundColor Green }
        "ERROR" { Write-Host "[!] $Message" -ForegroundColor Red }
        "HINT" { Write-Host "    $Message" -ForegroundColor Gray }
    }
    Start-Sleep -Milliseconds 300 # หน่วงเวลาให้คนอ่านทัน
}

# ==========================================
# เริ่มต้นการทำงาน (Main Execution)
# ==========================================

Clear-Host
Write-Host ""
Write-Host " OpenClaw Mockup Installer (Demo)" -ForegroundColor Cyan
Write-Host ""



function Install-Software {
    param(
        [string]$SoftwareName,
        [string]$SoftwarePath
    )
    Write-Host "Installing $SoftwareName..."
    Start-Process -FilePath $SoftwarePath -Wait
}


function setup_profile {
    param(
        [string]$SoftwareName,
        [string]$SoftwarePath
    )
    Write-Host "Installing $SoftwareName..."
    Start-Process -FilePath $SoftwarePath -Wait
}

# --- STEP 1: Interactive Menu (ที่คุณอยากเห็น) ---
$components = Invoke-InteractiveMenu -Title "Select components to simulate install:" -Options @(
    "Node.js Runtime",
    "Git Version Control",
    "OpenClaw Core System",
    "AI Model Dependencies",
    "Vector Database"
)

if ($components.Count -eq 0) {
    Show-Status -Message "No components selected. Exiting." -Type "ERROR"
    exit
}

Write-Host "`nStarting installation for: $($components -join ', ')...`n" -ForegroundColor Cyan
Start-Sleep -Seconds 1

# --- STEP 2: Process Simulation with Progress Bar ---
# ใช้ Write-Progress ซึ่งเป็น UI มาตรฐานของ PowerShell ที่ดูโปร
$total = $components.Count * 10
$current = 0

foreach ($comp in $components) {
    Show-Status -Message "Start process for $comp..." -Type "INFO"
    
    # จำลองการโหลด (Progress Bar)
    for ($i = 1; $i -le 10; $i++) {
        $current++
        $percent = ($current / ($components.Count * 10)) * 100
        Write-Progress -Activity "Installing Components" -Status "Processing $comp..." -PercentComplete $percent
        Start-Sleep -Milliseconds 100 # จำลองเวลาโหลด
    }
    
    # สุ่มสถานะเพื่อความสมจริง
    if ($comp -eq "Git Version Control") {
        Show-Status -Message "$comp already installed (Skipping)" -Type "HINT"
    }
    else {
        Show-Status -Message "$comp installed successfully" -Type "SUCCESS"
    }
}

# ปิด Progress Bar
Write-Progress -Activity "Installing Components" -Completed


