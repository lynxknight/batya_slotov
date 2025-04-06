docker build -t tennisbooking -f build/Dockerfile .
docker tag tennisbooking lynxknight/tennisbooking:latest
docker push lynxknight/tennisbooking:latest