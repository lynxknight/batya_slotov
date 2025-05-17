docker build -t tennisbooking -f build/Dockerfile .
docker tag tennisbooking lynxknight/tennisbooking:latest
docker push lynxknight/tennisbooking:latest && ssh 192.168.1.173 "/home/zhuk/pull_and_run_tennisbot.sh"