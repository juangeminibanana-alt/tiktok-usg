# Configuración de identidad local (para que el commit funcione)
git config user.email "jarc_@example.com"
git config user.name "Juan"

git init
git add .
git commit -m "Initial commit: Multi-agent TikTok pipeline"
git branch -M main

# Manejar el remoto si ya existe
git remote remove origin 2>$null
git remote add origin https://github.com/juangeminibanana-alt/tiktok-usg.git

git push -u origin main
