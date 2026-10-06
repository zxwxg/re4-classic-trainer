# Waits until the trainer is closed, then replaces the Desktop exe with the fresh build.
# Runs detached; writes its result next to this script.
$src = "C:\Users\nasse\OneDrive\Desktop\New folder\RE4ClassicTrainer\dist\RE4ClassicTrainer.exe"
$dst = "C:\Users\nasse\OneDrive\Desktop\RE4 Classic Trainer.exe"
$log = "C:\Users\nasse\OneDrive\Desktop\New folder\RE4ClassicTrainer\tools\deploy.log"
$want = (Get-Item $src).Length

"[{0}] waiting for the trainer to close..." -f (Get-Date -Format "HH:mm:ss") | Out-File $log -Encoding utf8
for ($i = 0; $i -lt 2000; $i++) {
    try {
        Copy-Item $src $dst -Force -ErrorAction Stop
        if ((Get-Item $dst).Length -eq $want) {
            "[{0}] deployed OK ({1} bytes)" -f (Get-Date -Format "HH:mm:ss"), $want |
                Out-File $log -Encoding utf8 -Append
            exit 0
        }
    } catch { }
    Start-Sleep -Seconds 3
}
"[{0}] gave up: file still locked" -f (Get-Date -Format "HH:mm:ss") | Out-File $log -Encoding utf8 -Append
exit 1
