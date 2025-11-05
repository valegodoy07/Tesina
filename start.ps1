$ErrorActionPreference = "Stop"

# Ir a la carpeta del script
Set-Location -Path (Split-Path -Parent $MyInvocation.MyCommand.Path)

# Activar entorno virtual si existe
if (Test-Path .\.venv\Scripts\Activate.ps1) {
  . .\.venv\Scripts\Activate.ps1
}

# Asegurar pip actualizado y dependencias instaladas
python -m pip install --upgrade pip
if (Test-Path .\requirements.txt) {
  pip install -r .\requirements.txt
} else {
  pip install Flask PyMySQL python-dotenv
}

# Configurar FLASK_APP y ejecutar
$env:FLASK_APP = "AppMenuDigital.Main:app"
flask run

