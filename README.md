# AutoDeploy
利用 paramiko 自动化部署 jar 包

---

## 解决的问题

公司的部署流程较为原始，当改变了某个组件包的时候，所有依赖的包需要重新上传到服务器，并且重启 Docker 中的服务。

本脚本将**重复性的上传，重启服务**通过配置文件的形式，来达到一键完成的效果

---

## 思路

采用`parammiko`的`SFTPClient`和`SSHClient`模块实现文件上传和控制服务器的脚本

---

## 配置文件格式

本项目采用的配置文件是 ini 文件，将 ini 文件和 main.py （或者打包好的 main.exe）放在一个目录下，配置好 ini 文件，执行 main.py（或者打包好的 main.exe）即可。

```ini
; 服务器信息
[address]
host=192.168.1.1
port=22

; 用户名和密码
[auth]
username=root
password=password

; 所需要上传的 map，用 ',' 隔开，中间不能有空格
; 将 map 列表中需要上传的文件，将 [] 里的名称写在这里
; 例如这里会上传 3 个文件并重启它们的服务
[include]
execute=leadmap-operation-server-rest,map3,map4

; 上传完文件后，是否重启服务，默认上传并重启
; 上传并且重启：true
; 上传但不重启：false
[restart_choice]
choice=true

; map 列表，对本地文件路径和远程路径的映射，以及重启服务脚本的地址信息
; [] 中的名字可以随便取，但一定要唯一，例如微服务的名称就可以
; local 代表本地放 jar 包的路径
; remote 代表服务器放 jar 包的路径
; restart 代表这个服务的重启脚本路径
; 路径都要采用绝对路径
; 并且需要精确到文件名，路径不能是文件夹结尾，后期这里可以优化，自动搜 jar 包和 shell 脚本
[leadmap-public-server-rest]
local=E:\newproject\leadmapCloudPlatform\leadmap-public-server\leadmap-public-server-rest\target\leadmap-public-server-rest.jar
remote=/usr/local/devtools/docker/leadmap-public-server/leadmap-public-server-rest.jar
restart=/usr/local/devtools/docker/leadmap-public-server/restart.sh

[leadmap-operation-server-rest]
local=E:\newproject\leadmapCloudPlatform\leadmap-operation-server\leadmap-operation-server-rest\target\leadmap-operation-server-rest.jar
remote=/usr/local/devtools/docker/leadmap-operation-server/leadmap-operation-server-rest.jar
restart=/usr/local/devtools/docker/leadmap-operation-server/restart.sh

[map3]
local=E:\newproject\leadmapCloudPlatform\leadmap-customer-management\leadmap-customer-rest\target\leadmap-customer-rest.jar
remote=/usr/local/devtools/docker/leadmap-customer-management/leadmap-customer-rest.jar
restart=/usr/local/devtools/docker/leadmap-customer-management/restart.sh

[map4]
local=E:\newproject\leadmapCloudPlatform\leadmap-auth\leadmap-auth-rest\target\leadmap-auth-rest.jar
remote=/usr/local/devtools/docker/leadmap-auth/leadmap-auth-rest.jar
restart=/usr/local/devtools/docker/leadmap-auth/restart.sh

[map5]
local=E:\领图科技\newproject\leadmapCloudPlatform\leadmap-gateway\target\leadmap-gateway.jar
remote=/usr/local/devtools/docker/leadmap-gateway/leadmap-gateway.jar
restart=/usr/local/devtools/docker/leadmap-gateway/restart.sh

[map6]
local=E:\newproject\leadmapCloudPlatform\leadmap-gis-server\leadmap-gis-server-rest\target\leadmap-gis-server-rest.jar
remote=/usr/local/devtools/docker/leadmap-gis-server/leadmap-gis-server-rest.jar
restart=/usr/local/devtools/docker/leadmap-gis-server/restart.sh

[map7]
local=E:\newproject\leadmapCloudPlatform\leadmap-platform-management\leadmap-platform-manage-rest\target\leadmap-platform-manage-rest.jar
remote=/usr/local/devtools/docker/leadmap-platform-management/leadmap-platform-manage-rest.jar
restart=/usr/local/devtools/docker/leadmap-platform-management/restart.sh
```

---

## 指定配置文件

当有多台服务器或者本地项目的时候，可以定义多个配置文件，如：

* config-测试环境.ini
* config-线上环境.ini
* 我的本地环境.ini

运行命令：

```
python .\main.py -c .\config-测试环境.ini
或者
.\main.exe -c .\config-测试环境.ini
```

---

## 变量插值

当有些字段重复过多的时候，可以采用变量插值语法

例如：

```ini
[leadmap-public-server-rest]
local=E:\newproject\leadmapCloudPlatform\leadmap-public-server\leadmap-public-server-rest\target\leadmap-public-server-rest.jar
remote=/usr/local/devtools/docker/leadmap-public-server/leadmap-public-server-rest.jar
restart=/usr/local/devtools/docker/leadmap-public-server/restart.sh

[leadmap-operation-server-rest]
local=E:\newproject\leadmapCloudPlatform\leadmap-operation-server\leadmap-operation-server-rest\target\leadmap-operation-server-rest.jar
remote=/usr/local/devtools/docker/leadmap-operation-server/leadmap-operation-server-rest.jar
restart=/usr/local/devtools/docker/leadmap-operation-server/restart.sh
```

可以改写成：

```ini
[variable]
local_path=E:\领图科技\newproject\leadmapCloudPlatform
remote_path=/usr/local/devtools/docker

[leadmap-public-server-rest]
local=${variable:local_path}\leadmap-public-server\leadmap-public-server-rest\target\leadmap-public-server-rest.jar
remote=${variable:remote_path}/leadmap-public-server/leadmap-public-server-rest.jar
restart=${variable:remote_path}/leadmap-public-server/restart.sh

[leadmap-operation-server-rest]
local=${variable:local_path}\leadmap-operation-server\leadmap-operation-server-rest\target\leadmap-operation-server-rest.jar
remote=${variable:remote_path}/leadmap-operation-server/leadmap-operation-server-rest.jar
restart=${variable:remote_path}/leadmap-operation-server/restart.sh
```
