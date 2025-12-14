
from utils.quark_api.quarkoperation import Quark
from utils.yml_utils.yml_operation import YmlOperation
from utils.module import DatabaseManager
from datetime import datetime
import functools
import os

def config_hot_reload(func):
    """配置热加载装饰器"""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if hasattr(self, '_check_config_update'):
            self._check_config_update()
        return func(self, *args, **kwargs)
    return wrapper

class QuarkController:
    def __init__(self, config_file=None):
        self.config_file = config_file if config_file else "config.yml"
        self.yml_operation = YmlOperation(self.config_file)
        self.yml_config = self.yml_operation.load_config()
        self.config_path = self.yml_operation.config_path
        self.config_mtime = os.path.getmtime(self.config_path)
        self.cookie = self.yml_config.get("cookie")
        print(f"cookie is {self.cookie}")
        self.quark = Quark(self.cookie)
        self.db_manager = DatabaseManager()
        self.conn = self.db_manager.get_connection()
        self.db_cursor = self.conn.cursor()

    def _check_config_update(self):
        """检查配置文件是否更新"""
        try:
            current_mtime = os.path.getmtime(self.config_path)
            if current_mtime > self.config_mtime:
                self._reload_config()
                self.config_mtime = current_mtime
        except Exception as e:
            print(f"检查配置文件更新时出错: {e}")

    def _reload_config(self):
        """重新加载配置文件"""
        try:
            self.yml = YmlOperation()
            self.config = self.yml.load_config()
            self.cookie = self.config.get('cookie', '')
            print("Quark配置文件已重新加载")
        except Exception as e:
            print(f"重新加载配置文件时出错: {e}")

    def format_bytes(self, size_bytes: int) -> str:
        units = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = 0
        while size_bytes >= 1024 and i < len(units) - 1:
            size_bytes /= 1024
            i += 1
        return f"{size_bytes:.2f} {units[i]}"

    # 分享链接
    def share_file(self, filidlist, title):
        task_id = self.quark.share_file_for_taskid(filidlist, title)
        share_id_res = self.quark.query_task(task_id)
        share_id = share_id_res["data"]["share_id"]
        res = self.quark.share_file(share_id)
        print(f"分享的结果： {res}")
        return res


    @config_hot_reload
    def save_file_and_get_share_url(self, task):
        """
        task dict 需要转存和分享的结构
        save_path  转存路径
        """
        # 转存
        zc_info, mbml_id = self.quark.do_save_task(task)
        print(f"转存的信息： {zc_info}")
        print(f"转存目标目录的ID： {mbml_id}")
        if not zc_info:
            return {"code":999, "msg":"资源不存在，请换一个"}
        if zc_info == {}:
            return {"code":405, "msg":"转存失败，请检查文件是否已存在", "data": task["shareurl"]}
        # 保存成功，记录到数据库
        quark_record_time = int(datetime.now().timestamp())
        # 插入文件记录并获取ID
        try:
            record_id = self.db_manager.insert_file_record(zc_info["data"]["fid"], zc_info["data"]["file_name_re"],task["share_type"],quark_record_time)
            print(f"插入的文件记录ID: {record_id}")
        except Exception as e:
            print(f"插入文件记录失败: {e}")
        # 分享
        share_res = self.share_file([zc_info["data"]["fid"]], zc_info["data"]["file_name_re"])
        print(f"分享结果： {share_res}")
        return {"code":200, "msg":"转存成功", "data": share_res}

    @config_hot_reload
    def delete_file(self, filid):
        res = self.quark.delete([filid])
        print(f"删除结果： {res}")
        return res


    @config_hot_reload
    def check_resource_valid(self, share_url):
        """
        检查资源是否有效
        """
        try:
            pwd_id, passcode, pdir_fid, _ = self.quark.extract_url(share_url)
            # 获取stoken，同时可验证资源是否失效
            get_stoken = self.quark.get_stoken(pwd_id, passcode)
            if get_stoken == {}:
                return False
            if get_stoken["code"] != 0:
                return False
            return True
        except Exception as e:
            print(f"检查资源有效性时出错: {e}")
            return True