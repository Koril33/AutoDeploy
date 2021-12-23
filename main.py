import time
import paramiko
import configparser
import os

class Address():
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def get_address_tuple(self):
        return (self.host, self.port)


class Auth():
    def __init__(self, username, password):
        self.username = username
        self.password = password


address = None
auth = None
restart_choice = True

'''
存储映射关系的列表
例如：
[
	{
		'local': 'C:\\Users\\Administrator\\Desktop\\test.txt', 
		'remote': '/usr/local/devtools/docker/test.txt',
		'restart': '/usr/local/devtools/docker/leadmap-public-server/restart.sh'
	}, 
	{
		'local': 'E:\\test2.txt', 
		'remote': '/usr/local/devtools/docker/test2.txt',
		'restart': '/usr/local/devtools/docker/leadmap-public-server/restart.sh'
	}
]
'''
map_list = list()

other_sections = ['address', 'auth', 'include', 'restart_choice']


def read_config():
    global address
    global auth
    global restart_choice

    cf = configparser.ConfigParser()
    cf.read('config.ini', encoding='utf-8')
    # 获取所有的配置节
    sections = cf.sections()

    address_list = cf.items('address')
    auth_list = cf.items('auth')

    address_dict = dict()
    for address_info_tuple in address_list:
        address_dict[address_info_tuple[0]] = address_info_tuple[1]
    auth_dict = dict()
    for auth_info_tuple in auth_list:
        auth_dict[auth_info_tuple[0]] = auth_info_tuple[1]

    address = Address(address_dict['host'], int(address_dict['port']))
    auth = Auth(auth_dict['username'], auth_dict['password'])

    # 用于指定上传哪些文件
    include_list = cf.items('include')[0][1].split(',')

    # 上传完以后是否重启
    restart_choice_config = cf.items('restart_choice')[0][1]
    if (restart_choice_config == 'false'):
        restart_choice = False

    for section in other_sections:
        sections.remove(section)

    # 遍历所有 map，构造映射关系的列表
    for section in sections:
        if section not in include_list:
            continue
        item = cf.items(section)
        local_info = item[0]
        remote_info = item[1]
        restart_info = item[2]

        d = dict()
        d[local_info[0]] = local_info[1]
        d[remote_info[0]] = remote_info[1]
        d[restart_info[0]] = restart_info[1]

        map_list.append(d)


def transport_file(address, auth, local_path, remote_path):
    if address is None:
        raise Exception('address 不能为 None')
    if auth is None:
        raise Exception('auth 不能为 None')
    print(
        f'-----------------开始上传-------------------\n'
        f'将本地文件:[{local_path}]\n'
        f'上传至服务器: [{address.get_address_tuple()}]， 路径: [{remote_path}]\n'
    )
    start_time = time.time()

    # 获取Transport实例
    tran = paramiko.Transport(address.get_address_tuple())

    # 连接SSH服务端，使用用户名和密码的方式
    tran.connect(username=auth.username, password=auth.password)

    # 或使用
    # 配置私人密钥文件位置
    # private = paramiko.RSAKey.from_private_key_file('/Users/root/.ssh/id_rsa')
    # 连接SSH服务端，使用pkey指定私钥
    # tran.connect(username="root", pkey=private)

    # 获取SFTP实例
    sftp = paramiko.SFTPClient.from_transport(tran)

    # 执行上传动作
    sftp.put(localpath=local_path, remotepath=remote_path)
    # 执行下载动作
    # sftp.get(remotepath, localpath)

    tran.close()
    end_time = time.time()
    print(f'-----------------上传完成，耗时：[{end_time - start_time}]秒-------------------\n')


def execute_restart(address, auth, cmd, timeout=10):
    try:
        ssh = paramiko.SSHClient()  # 创建一个新的SSHClient实例
        ssh.banner_timeout = timeout
        # 设置host key,如果在"known_hosts"中没有保存相关的信息, SSHClient 默认行为是拒绝连接, 会提示yes/no
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(address.host, int(address.port), auth.username, auth.password, timeout=timeout)  # 连接远程服务器,超时时间1秒
        stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True, timeout=timeout)  # 执行命令
        result_info = stdout.readlines()  # 执行结果,readlines会返回列表
        # 执行状态,0表示成功，1表示失败
        channel = stdout.channel
        status = channel.recv_exit_status()
        ssh.close()  # 关闭ssh连接
        for info in result_info:
            print(info)
    except Exception as e:
        print(e)
        print(f'错误, 服务器执行命令错误！ip: {address.get_address_tuple()} 命令: {cmd}')


def generator_cmd(restart_path):
    path = restart_path.rpartition('/')[0]
    return 'cd ' + path + ' && . ' + restart_path


def upload_restart(map_list):
    for file_path_info in map_list:
        local_path = file_path_info['local']
        remote_path = file_path_info['remote']
        transport_file(address, auth, local_path, remote_path)
        print('---------------文件上传完毕---------------')
        if restart_choice:
            restart_path = file_path_info['restart']
            cmd = generator_cmd(restart_path)
            print(f'执行重启命令，cmd: [{cmd}]')
            execute_restart(address, auth, cmd)
            print('---------------服务重启完成---------------')
        else:
            print('---------------不选择重启---------------')

def main():
    # 读取配置
    read_config()
    upload_restart(map_list)


if __name__ == '__main__':
    main()
    os.system('pause')
