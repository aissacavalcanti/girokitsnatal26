@echo off
cd /d "%~dp0"
echo.
echo === Preparar publicacao do StockBridge Giro ===
echo Copia a ultima base deste PC para data\publicada
echo (essa pasta vai no GitHub e aparece no dash compartilhado).
echo.

if not exist "data\ultima\vendas.csv" (
  echo ERRO: Nao achei data\ultima\vendas.csv
  echo Abra o app, va em Dados e envie ABC + Saldo antes.
  pause
  exit /b 1
)
if not exist "data\ultima\estoque.csv" (
  echo ERRO: Nao achei data\ultima\estoque.csv
  pause
  exit /b 1
)

if not exist "data\publicada" mkdir "data\publicada"

copy /Y "data\ultima\vendas.csv" "data\publicada\vendas.csv" >nul
copy /Y "data\ultima\estoque.csv" "data\publicada\estoque.csv" >nul

if exist "data\ultima\dcentro.csv" (
  copy /Y "data\ultima\dcentro.csv" "data\publicada\dcentro.csv" >nul
) else if exist "data\ultima\dcentro.xlsx" (
  copy /Y "data\ultima\dcentro.xlsx" "data\publicada\dcentro.xlsx" >nul
) else (
  copy /Y "data\dcentros.csv" "data\publicada\dcentro.csv" >nul
)

if exist "data\ultima\classificacao.csv" (
  copy /Y "data\ultima\classificacao.csv" "data\publicada\classificacao.csv" >nul
)

if exist "data\ultima\meta.json" (
  copy /Y "data\ultima\meta.json" "data\publicada\meta.json" >nul
) else (
  echo {"atualizado_em":"%DATE% %TIME%","origem":"preparar_publicacao"}> "data\publicada\meta.json"
)

echo Pronto. Pasta data\publicada atualizada.
echo.
echo Proximos passos:
echo  1. Commit + push no GitHub
echo  2. No Streamlit Cloud, o app redeploya sozinho
echo  3. Compartilhe o link + a senha APP_PASSWORD com a equipe
echo.
pause
