function Show-Banner {
    Clear-Host
    $lines = @(
        '██╗████████╗    ███████╗██╗   ██╗██████╗ ██████╗  ██████╗ ██████╗ ████████╗',
        '██║╚══██╔══╝    ██╔════╝██║   ██║██╔══██╗██╔══██╗██╔═══██╗██╔══██╗╚══██╔══╝',
        '██║   ██║       ███████╗██║   ██║██████╔╝██████╔╝██║   ██║██████╔╝   ██║   ',
        '██║   ██║       ╚════██║██║   ██║██╔═══╝ ██╔═══╝ ██║   ██║██╔══██╗   ██║   ',
        '██║   ██║       ███████║╚██████╔╝██║     ██║     ╚██████╔╝██║  ██║   ██║   ',
        '╚═╝   ╚═╝       ╚══════╝ ╚═════╝ ╚═╝     ╚═╝      ╚═════╝ ╚═╝  ╚═╝   ╚═╝   '
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

Show-Banner
