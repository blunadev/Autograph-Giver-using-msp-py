@echo off
REM === Configuration ===
set PYTHON=C:\Users\jims\AppData\Local\Programs\Python\Python39\python.exe
set PYINSTALLER=%PYTHON% -m PyInstaller
set ICON=jims.ico
set SCRIPT=autos.py
set MSPDLL=C:\Users\jims\AppData\Local\Programs\Python\Python39\Lib\site-packages\msp_tls_client\dependencies\tls-client-64.dll

REM === Clean old build ===
echo Cleaning old build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist %SCRIPT:.py=.spec% del %SCRIPT:.py=.spec%

REM === Build ===
echo Building executable...
%PYINSTALLER% --onefile --clean --icon=%ICON% ^
--add-data "%MSPDLL%;msp_tls_client/dependencies" ^
--collect-all pyamf ^
%SCRIPT%

echo.
echo Build finished!
echo Your EXE will be inside the "dist" folder.
pause
