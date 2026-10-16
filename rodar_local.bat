@echo off
cd /d "%~dp0"
echo StockBridge Giro — somente local (127.0.0.1)
echo Nao publica na internet. Feche esta janela para encerrar.
echo.
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
pause
