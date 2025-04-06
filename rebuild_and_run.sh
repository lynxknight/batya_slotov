docker build -t tennisbooking -f build/Dockerfile .
docker run -d -e TENNIS_USERNAME=$(cat .sensitive/.username) -e TENNIS_PASSWORD=$(cat .sensitive/.password) -e TENNIS_BOT_TOKEN=$(cat .sensitive/.telegram_bot_token) tennisbooking
echo "Docker run status: $?"
