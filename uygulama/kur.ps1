# CatiGunes web uygulamasini bu bilgisayarda kurar (bir kez calistirilir).
#  1. Docker'da PostgreSQL + PostGIS veritabanini kurar (catigunes_db container'i)
#  2. veritabani/yedek/catigunes_web.sql dokumunu yukler (1.085 cati + yapay zeka yorumlari)
#  3. Asistanin kullandigi salt okunur 'sorgu_okur' kullanicisini olusturur
#  4. web/.venv Python ortamini kurar
#  5. web/.env dosyasini yazar (Gemini anahtari sorulur)
# Kullanim: kur.bat dosyasina cift tiklayin.
param(
  [string]$Container = "catigunes_db",
  [int]$Port = 5432,
  [string]$Imaj = "postgis/postgis:17-3.5",
  [string]$GeminiAnahtar = $null,   # verilmezse sorulur
  [switch]$Yenile                    # catigunes_web varsa sormadan yeniden kur
)
# Docker uyarilarini stderr'e yazar; PowerShell 5.1 bunlari hata sanmasin. Gercek hatalar cikis koduyla yakalanir.
$ErrorActionPreference = "Continue"
trap { Write-Host ""; Write-Host "HATA: $_" -ForegroundColor Red; exit 1 }
$kok = Split-Path -Parent $MyInvocation.MyCommand.Path
function Adim($m) { Write-Host ""; Write-Host "==> $m" -ForegroundColor Yellow }
function Dock { & docker @args; if ($LASTEXITCODE -ne 0) { throw "docker $($args -join ' ') basarisiz" } }

# 1. Docker
Adim "Docker kontrol ediliyor"
docker info *> $null
if ($LASTEXITCODE -ne 0) {
  $dd = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
  if (-not (Test-Path $dd)) { throw "Docker Desktop kurulu degil. https://www.docker.com/products/docker-desktop adresinden kurun." }
  Write-Host "Docker Desktop baslatiliyor, 1-2 dakika surebilir..."
  Start-Process $dd
  $hazir = $false
  for ($i = 0; $i -lt 60; $i++) { Start-Sleep 5; docker info *> $null; if ($LASTEXITCODE -eq 0) { $hazir = $true; break } }
  if (-not $hazir) { throw "Docker Desktop acilmadi. Elle acip kur.bat'i tekrar calistirin." }
}

# 2. Veritabani container'i
Adim "Veritabani container'i ($Container)"
$var = docker ps -a --filter "name=^$Container$" --format "{{.Names}}"
if (-not $var) {
  $dbSifre = "password"
  Dock run -d --name $Container -e "POSTGRES_PASSWORD=$dbSifre" -p "${Port}:5432" $Imaj | Out-Null
  Write-Host "Yeni container olusturuldu ($Imaj, port $Port). Ilk kurulum bekleniyor..."
  # imaj ilk acilista gecici bir sunucuyla PostGIS'i kurup yeniden baslar; bu bitmeden baglanilmaz
  $bitti = $false
  for ($i = 0; $i -lt 90; $i++) {
    Start-Sleep 2
    $log = cmd /c "docker logs $Container 2>&1" | Out-String
    if ($log -match "PostgreSQL init process complete") { $bitti = $true; break }
  }
  if (-not $bitti) { throw "Veritabani ilk kurulumu bitmedi. 'docker logs $Container' ile kontrol edin." }
} else {
  Dock start $Container | Out-Null
  $dbSifre = (docker inspect $Container --format "{{range .Config.Env}}{{println .}}{{end}}" | Select-String "^POSTGRES_PASSWORD=").ToString().Split("=", 2)[1]
  $Port = [int](docker inspect $Container --format '{{(index (index .NetworkSettings.Ports \"5432/tcp\") 0).HostPort}}')
  Write-Host "Mevcut container kullaniliyor (port $Port)."
}
for ($i = 0; $i -lt 60; $i++) { docker exec $Container pg_isready -U postgres *> $null; if ($LASTEXITCODE -eq 0) { break }; Start-Sleep 2 }
Start-Sleep 2

# 3. Dokum
Adim "Veri yukleniyor (catigunes_web)"
$mevcut = docker exec $Container psql -U postgres -Atc "SELECT 1 FROM pg_database WHERE datname = 'catigunes_web'"
$yukle = $true
if ($mevcut -eq "1") {
  if (-not $Yenile) {
    $c = Read-Host "catigunes_web veritabani zaten var. Silinip repodaki haliyle yeniden kurulsun mu? (E/H)"
    $yukle = $c -match "^[eEyY]"
  }
  if ($yukle) { Dock exec $Container psql -U postgres -qc "DROP DATABASE catigunes_web WITH (FORCE)" | Out-Null }
}
if ($yukle) {
  Dock exec $Container psql -U postgres -qc "CREATE DATABASE catigunes_web" | Out-Null
  Dock cp "$kok\veritabani\yedek\catigunes_web.sql" "${Container}:/tmp/catigunes_web.sql"
  Dock exec $Container psql -U postgres -d catigunes_web -v ON_ERROR_STOP=1 -q -o /dev/null -f /tmp/catigunes_web.sql
  $n = docker exec $Container psql -U postgres -d catigunes_web -Atc "SELECT count(*) FROM v_cati"
  Write-Host "Yuklendi: $n cati."
} else { Write-Host "Mevcut veritabani korundu." }

# 4. Salt okunur kullanici
Adim "Asistan icin salt okunur kullanici"
$okurSifre = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 24 | ForEach-Object { [char]$_ })
Dock cp "$kok\veritabani\sorgu_kullanicisi.sql" "${Container}:/tmp/sorgu_kullanicisi.sql"
Dock exec $Container psql -U postgres -d catigunes_web -v ON_ERROR_STOP=1 -q -v "sifre='$okurSifre'" -f /tmp/sorgu_kullanicisi.sql | Out-Null

# 5. Python ortami
Adim "Python ortami (web\.venv)"
$web = Join-Path $kok "web"
$venvPy = Join-Path $web ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
  if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv (Join-Path $web ".venv") }
  elseif (Get-Command python -ErrorAction SilentlyContinue) { & python -m venv (Join-Path $web ".venv") }
  else { throw "Python bulunamadi. https://www.python.org adresinden Python 3.11+ kurun." }
}
& $venvPy -m pip install -q --disable-pip-version-check -r (Join-Path $web "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Paketler kurulamadi." }

# 6. .env
Adim "Ayar dosyasi (web\.env)"
$envYol = Join-Path $web ".env"
$eski = $null
if (Test-Path $envYol) { $eski = (Get-Content $envYol | Select-String "^GEMINI_API_KEY=").Line }
if (-not $GeminiAnahtar) {
  if ($eski) {
    $c = Read-Host "Kayitli Gemini anahtari kullanilsin mi? (E/H)"
    if ($c -match "^[eEyY]") { $GeminiAnahtar = $eski.Split("=", 2)[1] }
  }
  if (-not $GeminiAnahtar) {
    Write-Host "Asistan (chatbot) icin Google Gemini API anahtari gerekir. Ucretsiz almak icin: https://aistudio.google.com/apikey"
    $GeminiAnahtar = Read-Host "Gemini API anahtari (bos birakirsaniz asistan calismaz, sitenin geri kalani calisir)"
  }
}
$satirlar = @(
  "DATABASE_URL=postgresql://postgres:$dbSifre@localhost:$Port/catigunes_web",
  "SORGU_DATABASE_URL=postgresql://sorgu_okur:$okurSifre@localhost:$Port/catigunes_web",
  "GEMINI_API_KEY=$GeminiAnahtar"
)
[IO.File]::WriteAllLines($envYol, $satirlar, (New-Object Text.UTF8Encoding $false))

Write-Host ""
Write-Host "Kurulum tamam. Siteyi acmak icin web\baslat.bat dosyasina cift tiklayin, sonra http://localhost:8000 adresine gidin." -ForegroundColor Green
