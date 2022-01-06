import time
import paramiko
import configparser
import os
import argparse
import logging
from configparser import ExtendedInterpolation
from tqdm import tqdm


class Address:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def get_address_tuple(self):
        return self.host, self.port


class Auth:
    def __init__(self, username, password):
        self.username = username
        self.password = password


class MapPath:
    def __init__(self, map_name, local_path, remote_path, restart_script_path):
        self.map_name = map_name
        self.local_path = local_path
        self.remote_path = remote_path
        self.restart_script_path = restart_script_path

    def __repr__(self):
        return self.map_name


class Config:
    def __init__(self, config_file_name=None):
        # config_section 代表所有固定的配置项，除了下面以外的配置项都是地址映射
        self.config_section = {
            'ADDRESS': 'address',
            'AUTH': 'auth',
            'INCLUDE': 'include',
            'RESTART_CHOICE': 'restart_choice',
            'VARIABLE': 'variable'
        }
        # 配置文件地址
        self.config_file_name = config_file_name
        # 服务器地址
        self.address = None
        # 服务器用户信息
        self.auth = None
        # 是否重启
        # True: 重启
        # False: 不重启
        self.restart_flag = True
        # 配置文件中所有文件的名称列表
        self.map_info_list = None
        # 需要上传文件的名称列表
        self.upload_file_list = None
        self.map_list = list()

    def get_arg(self):
        parser = argparse.ArgumentParser(description='Test for argparse')
        parser.add_argument('--config', '-c', help='设置配置文件', default='config-测试.ini')
        args = parser.parse_args()
        self.config_file_name = args.config

    def read_config(self):
        self.get_arg()
        logging.info(f'读取配置文件：{self.config_file_name}')
        cf = configparser.ConfigParser(interpolation=ExtendedInterpolation(),
                                       inline_comment_prefixes=['#', ';'],
                                       allow_no_value=True)

        cf.read(self.config_file_name, encoding='utf-8')

        # 获取所有的配置节
        sections = cf.sections()
        # 服务器地址信息[('host', '192.168.1.62'), ('port', '22')]
        address_info_list = cf.items('address')
        # 服务器用户名和密码[('username', 'root'), ('password', '123456')]
        auth_info_list = cf.items('auth')

        address_info_dict = {address_info[0]: address_info[1] for address_info in address_info_list}
        auth_info_dict = {auth_info[0]: auth_info[1] for auth_info in auth_info_list}

        self.address = Address(address_info_dict['host'], int(address_info_dict['port']))
        self.auth = Auth(auth_info_dict['username'], auth_info_dict['password'])

        # 上传完以后是否重启
        restart_choice_config = cf.items('restart_choice')[0][1]
        if restart_choice_config == 'false':
            self.restart_flag = False

        # 所有的 map 映射路径的 section 配置名称列表
        self.map_info_list = [
            map_info
            for map_info in sections
            if map_info not in self.config_section.values()
        ]

        # 所有需要上传的 map
        # 如果配置的内容是 all 就上传全部
        include_info = cf.items('include')[0][1]
        if include_info == 'all':
            self.upload_file_list = self.map_info_list
        else:
            self.upload_file_list = include_info.split(',')

        # 遍历所有 map，构造映射关系的列表
        for map_name in self.upload_file_list:
            map_info = cf.items(map_name)
            m = MapPath(
                map_name,
                map_info[0][1],
                map_info[1][1],
                map_info[2][1]
            )

            self.map_list.append(m)


class Server:
    def __init__(self, address, auth, config):
        self.address = address
        self.auth = auth
        self.config = config
        if config.restart_flag:
            self.result = Result(config.upload_file_list, config.upload_file_list)
        else:
            self.result = Result(config.upload_file_list, [])

    def transport_file(self, local_path, remote_path):
        if self.address is None:
            raise Exception('address 不能为 None')
        if self.auth is None:
            raise Exception('auth 不能为 None')

        logging.info(f'将本地文件: [{local_path}] '
                     f'上传至服务器: [{self.address.get_address_tuple()}], '
                     f'存储路径: [{remote_path}]')

        start_time = time.time()

        # 获取Transport实例
        tran = paramiko.Transport(self.address.get_address_tuple())

        # 连接SSH服务端，使用用户名和密码的方式
        tran.connect(username=self.auth.username, password=self.auth.password)

        # 或使用
        # 配置私人密钥文件位置
        # private = paramiko.RSAKey.from_private_key_file('/Users/root/.ssh/id_rsa')
        # 连接SSH服务端，使用pkey指定私钥
        # tran.connect(username="root", pkey=private)

        # 获取SFTP实例
        sftp = paramiko.SFTPClient.from_transport(tran)

        # 执行上传动作
        # sftp.put(localpath=local_path, remotepath=remote_path)
        cbk, pbar = tqdmWrapViewBar(
            ascii=True,
            unit='b',
            unit_scale=True,
            ncols=100,
            postfix='上传中',
            colour='green'
        )
        sftp.put(localpath=local_path, remotepath=remote_path, callback=cbk)
        pbar.close()

        # 执行下载动作
        # sftp.get(remotepath, localpath)

        tran.close()
        end_time = time.time()
        logging.info(f'上传完成！耗时: [{round(end_time - start_time, 3)} 秒]')

    def execute_restart(self, cmd, timeout=10):
        try:
            ssh = paramiko.SSHClient()  # 创建一个新的SSHClient实例
            ssh.banner_timeout = timeout

            # 设置host key,如果在"known_hosts"中没有保存相关的信息, SSHClient 默认行为是拒绝连接, 会提示yes/no
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            ssh.connect(
                self.address.host,
                int(self.address.port),
                self.auth.username,
                self.auth.password,
                timeout=timeout
            )
            # 执行命令
            stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True, timeout=timeout)
            # 执行结果, readlines 返回列表
            result_info = stdout.readlines()
            # 执行状态,0表示成功，1表示失败
            channel = stdout.channel
            status = channel.recv_exit_status()
            ssh.close()  # 关闭ssh连接
            for info in result_info:
                logging.info(info.rstrip('\n'))
            self.result.success_restart_list.append(cmd)
        except Exception as e:
            logging.error(e)
            logging.error(f'错误, 服务器执行命令错误！ip: {self.address.get_address_tuple()} 命令: {cmd}')
            self.result.fail_restart_list.append(cmd)

    def generator_cmd(self, restart_path):
        path = restart_path.rpartition('/')[0]
        return 'cd ' + path + ' && . ' + restart_path

    def upload_restart(self):
        logging.info(f'上传文件: {self.config.map_list}, 共 {len(self.config.map_list)} 个')
        for map_info in self.config.map_list:
            local_path = map_info.local_path
            remote_path = map_info.remote_path
            self.transport_file(local_path, remote_path)
            self.result.success_upload_list.append(local_path)

            if self.config.restart_flag:
                restart_path = map_info.restart_script_path
                cmd = self.generator_cmd(restart_path)
                logging.info(f'执行重启命令，cmd: [{cmd}]')
                self.execute_restart(cmd)
            else:
                logging.info(f'不进行重启服务')


class Result:
    def __init__(self, expect_upload_list=None, expect_restart_list=None):
        # 实际成功上传文件列表
        self.success_upload_list = []
        # 实际失败上传文件列表
        self.fail_upload_list = []
        # 实际成功重启服务列表
        self.success_restart_list = []
        # 实际失败重启服务列表
        self.fail_restart_list = []

        self.expect_upload_list = expect_upload_list
        self.expect_restart_list = expect_restart_list


def tqdmWrapViewBar(*args, **kwargs):
    pbar = tqdm(*args, **kwargs)  # make a progressbar
    last = [0]  # last known iteration, start at 0

    def viewBar2(a, b):
        pbar.total = int(b)
        pbar.update(int(a - last[0]))  # update pbar with increment
        last[0] = a  # update last known iteration

    return viewBar2, pbar  # return callback, tqdmInstance


def main():
    config = Config()
    config.read_config()
    server = Server(config.address, config.auth, config)
    server.upload_restart()
    result = server.result
    logging.info('---------------------执行结束---------------------')
    logging.info(f'期望上传: {result.expect_upload_list}, 共 {len(result.expect_upload_list)} 个')
    logging.info(f'实际上传: {result.success_upload_list}, 共 {len(result.success_upload_list)} 个')
    logging.info(f'期望重启: {result.expect_restart_list}, 共 {len(result.expect_restart_list)} 个')
    logging.info(f'实际重启: {result.success_restart_list}, 共 {len(result.success_restart_list)} 个')
    logging.info(f'失败上传: {result.fail_upload_list}, 共 {len(result.fail_upload_list)} 个')
    logging.info(f'失败重启: {result.fail_restart_list}, 共 {len(result.fail_restart_list)} 个')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='\033[1;36m <%(asctime)s> \033[0m - \033[1;35m <%(name)s> \033[0m - \033[1;34m <%(levelname)s> \033[0m - <%(message)s>')
    logger = logging.getLogger(__name__)
    main()
    os.system('pause')
