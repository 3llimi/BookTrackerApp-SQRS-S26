Set-Location -Path (Join-Path $PSScriptRoot "..")
poetry run streamlit run --theme.base dark
