# 语法：docker save -o 导出文件路径 镜像名:标签
docker build -t blinko-wx-svr-alpine:v1.0 .
docker save -o blinko-wx-svr-alpine.tar blinko-wx-svr-alpine:v1.0
scp -Cp blinko-wx-svr-alpine.tar  ario@192.168.50.118:/home/ario/