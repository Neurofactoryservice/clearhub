@echo off
chcp 65001 >nul
echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║  Fix liens Stripe — ClearHub                        ║
echo ╚══════════════════════════════════════════════════════╝
echo.

set SITE_DIR=%~dp0
set STRIPE_LINK=https://buy.stripe.com/fZu9ATb979v69JFgUE7EQ01
set OLD_PATTERN=buy.stripe.com/mock_clearhub

echo Dossier : %SITE_DIR%
echo Nouveau lien : %STRIPE_LINK%
echo.

:: Vérifier que Python est disponible
python --version >nul 2>&1
if errorlevel 1 (
    echo ERREUR: Python non trouvé. Installez Python et réessayez.
    pause
    exit /b 1
)

:: Script Python inline pour remplacer dans tous les fichiers
python -c "
import os, sys, glob

site_dir = r'%SITE_DIR%'
old = 'buy.stripe.com/mock_clearhub'
new = 'buy.stripe.com/fZu9ATb979v69JFgUE7EQ01'
old_full = 'https://buy.stripe.com/mock_clearhub'

extensions = ['*.html', '*.js', '*.py']
total = 0

for ext in extensions:
    for fpath in glob.glob(os.path.join(site_dir, ext)):
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            if old in content:
                new_content = content.replace(old, new)
                with open(fpath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                count = content.count(old)
                total += count
                print(f'  OK ({count}x) : {os.path.basename(fpath)}')
        except Exception as e:
            print(f'  ERREUR {os.path.basename(fpath)}: {e}')

print()
if total > 0:
    print(f'  {total} lien(s) remplace(s) avec succes')
else:
    print('  Aucun lien mock trouve — verifiez que ce script est dans le bon dossier')
"

echo.
echo ══════════════════════════════════════════════════════
echo  Push vers GitHub...
echo ══════════════════════════════════════════════════════
echo.

cd /d "%SITE_DIR%"
git add .
git commit -m "fix: real Stripe payment link"
git push

if errorlevel 1 (
    echo.
    echo ATTENTION: Git push echoue. Faites-le manuellement.
) else (
    echo.
    echo OK - Modifications poussees sur GitHub
    echo Render va se redeployer automatiquement.
)

echo.
pause
