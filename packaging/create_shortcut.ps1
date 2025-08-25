
Param(
  [string]$DistPath = ".\dist\BitD_GM_AI",
  [string]$Name = "BitD GM AI"
)
$Shell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath("Desktop")
$Shortcut = $Shell.CreateShortcut( (Join-Path $Desktop "$Name.lnk") )
$Shortcut.TargetPath = (Join-Path (Resolve-Path $DistPath) "$Name.exe")
$Shortcut.WorkingDirectory = (Resolve-Path $DistPath)
$Shortcut.IconLocation = (Join-Path (Resolve-Path ".") "packaging\bitd_gm_ai.ico")
$Shortcut.Save()
Write-Host "Created desktop shortcut: $Desktop\$Name.lnk"
