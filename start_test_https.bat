@echo off
setlocal
chcp 65001 >nul
title Cloudflare Tunnel - Pharmacie pilote

echo ==========================================================
echo   TUNNEL HTTPS TEMPORAIRE - Test GPS sur iPhone
echo ==========================================================
echo.

REM --- 1. Verifier que le serveur local repond -----------------
echo [1/4] Verification du serveur local (http://127.0.0.1:8000)...
curl -s -o nul -w "    HTTP %%{http_code}\n" http://127.0.0.1:8000
if errorlevel 1 goto ERR_SERVER

REM --- 2. Verifier si cloudflared est installe ----------------
echo.
echo [2/4] Verification de cloudflared...
where cloudflared >nul 2>&1
if errorlevel 1 goto INSTALL

echo     cloudflared deja installe.
goto RUN

:INSTALL
echo     cloudflared absent. Installation via winget...
where winget >nul 2>&1
if errorlevel 1 goto ERR_WINGET

winget install --id Cloudflare.cloudflared -e --accept-source-agreements --accept-package-agreements
if errorlevel 1 goto ERR_INSTALL

REM Rafraichir le PATH dans cette session
set "PATH=%PATH%;%LOCALAPPDATA%\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe"

where cloudflared >nul 2>&1
if errorlevel 1 goto ERR_PATH

:RUN
echo.
echo [3/4] Version installee :
cloudflared --version

echo.
echo [4/4] Ouverture du tunnel HTTPS...
echo.
echo ==========================================================
echo   IMPORTANT : cherchez la ligne "trycloudflare.com"
echo   qui va s'afficher ci-dessous. C'est votre URL HTTPS.
echo.
echo   Cette URL est TEMPORAIRE (elle expire a la fermeture).
echo   Aucun compte Cloudflare n'est necessaire.
echo ==========================================================
echo.
echo Pour arreter le tunnel : Ctrl+C dans cette fenetre.
echo.

cloudflared tunnel --url http://127.0.0.1:8000
goto END

:ERR_SERVER
echo.
echo [ERREUR] Le serveur local ne repond pas sur http://127.0.0.1:8000.
echo Lancez d'abord :  uvicorn main:app --reload --host 0.0.0.0 --port 8000
pause
exit /b 1

:ERR_WINGET
echo.
echo [ERREUR] winget introuvable. Installez cloudflared manuellement :
echo   https://github.com/cloudflare/cloudflared/releases
echo   (choisir cloudflared-windows-amd64.exe, renommer en cloudflared.exe,
echo    placer dans C:\Windows\System32\ ou ajouter au PATH)
pause
exit /b 1

:ERR_INSTALL
echo.
echo [ERREUR] L'installation via winget a echoue.
echo Relancez ce script en tant qu'administrateur si necessaire.
pause
exit /b 1

:ERR_PATH
echo.
echo [ERREUR] cloudflared installe mais introuvable dans le PATH de cette session.
echo Solution : fermez cette fenetre, ouvrez un nouveau CMD, relancez ce .bat.
pause
exit /b 1

:END
pause