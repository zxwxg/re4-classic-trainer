# Captures a window (by process name) into a PNG using PrintWindow - works even if the
# window is covered. Usage: powershell -File shot.ps1 -ProcessName "RE4 Classic Trainer" -Out out.png
param(
  [string]$ProcessName = "RE4 Classic Trainer",
  [string]$Out = "C:\Users\nasse\OneDrive\Desktop\New folder\RE4ClassicTrainer\tools\shot.png"
)

Add-Type -AssemblyName System.Drawing

$sig = @'
using System;
using System.Runtime.InteropServices;
public class Win32Shot {
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, uint nFlags);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
}
'@
if (-not ("Win32Shot" -as [type])) { Add-Type -TypeDefinition $sig }

$proc = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $proc) { Write-Output "no window found for '$ProcessName'"; exit 1 }

$h = $proc.MainWindowHandle
[void][Win32Shot]::ShowWindow($h, 9)      # SW_RESTORE
[void][Win32Shot]::SetForegroundWindow($h)
Start-Sleep -Milliseconds 700

$r = New-Object Win32Shot+RECT
[void][Win32Shot]::GetWindowRect($h, [ref]$r)
$w = $r.Right - $r.Left
$hgt = $r.Bottom - $r.Top
if ($w -le 0 -or $hgt -le 0) { Write-Output "bad window rect"; exit 1 }

$bmp = New-Object System.Drawing.Bitmap($w, $hgt)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
[void][Win32Shot]::PrintWindow($h, $hdc, 2)   # PW_RENDERFULLCONTENT
$g.ReleaseHdc($hdc)
$g.Dispose()
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output ("saved {0} ({1}x{2})" -f $Out, $w, $hgt)
