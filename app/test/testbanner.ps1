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

Show-Banner
