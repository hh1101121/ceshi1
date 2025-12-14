# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# Modify: 2025-09-05
# Repo: https://github.com/Cp0204/quark_auto_save
# ConfigFile: quark_config.json
"""
new Env('夸克自动追更');
0 8,18,20 * * * quark_auto_save.py
"""
import os
import re
import sys
import json
import time
import random
import requests
import importlib
import traceback
import urllib.parse
import string
from datetime import datetime
from natsort import natsorted
# import yml_utils
# from yml_utils.yml_operation import YmlOperation

import random
import string

# 兼容青龙
try:
    from treelib import Tree
except:
    print("正在尝试自动安装依赖...")
    os.system("pip3 install treelib &> /dev/null")
    from treelib import Tree

CONFIG_DATA = {}
GH_PROXY = os.environ.get("GH_PROXY", "https://ghproxy.net/")


class MagicRename:
    magic_regex = {
        "$TV": {
            "pattern": r".*?([Ss]\d{1,2})?(?:[第EePpXx\.\-\_\( ]{1,2}|^)(\d{1,3})(?!\d).*?\.(mp4|mkv)",
            "replace": r"\1E\2.\3",
        },
        "$BLACK_WORD": {
            "pattern": r"^(?!.*纯享)(?!.*加更)(?!.*超前企划)(?!.*训练室)(?!.*蒸蒸日上).*",
            "replace": "",
        },
    }

    magic_variable = {
        "{TASKNAME}": "",
        "{I}": 1,
        "{EXT}": [r"(?<=\.)\w+$"],
        "{CHINESE}": [r"[\u4e00-\u9fa5]{2,}"],
        "{DATE}": [
            r"(18|19|20)?\d{2}[\.\-/年]\d{1,2}[\.\-/月]\d{1,2}",
            r"(?<!\d)[12]\d{3}[01]?\d[0123]?\d",
            r"(?<!\d)[01]?\d[\.\-/月][0123]?\d",
        ],
        "{YEAR}": [r"(?<!\d)(18|19|20)\d{2}(?!\d)"],
        "{S}": [r"(?<=[Ss])\d{1,2}(?=[EeXx])", r"(?<=[Ss])\d{1,2}"],
        "{SXX}": [r"[Ss]\d{1,2}(?=[EeXx])", r"[Ss]\d{1,2}"],
        "{E}": [
            r"(?<=[Ss]\d\d[Ee])\d{1,3}",
            r"(?<=[Ee])\d{1,3}",
            r"(?<=[Ee][Pp])\d{1,3}",
            r"(?<=第)\d{1,3}(?=[集期话部篇])",
            r"(?<!\d)\d{1,3}(?=[集期话部篇])",
            r"(?!.*19)(?!.*20)(?<=[\._])\d{1,3}(?=[\._])",
            r"^\d{1,3}(?=\.\w+)",
            r"(?<!\d)\d{1,3}(?!\d)(?!$)",
        ],
        "{PART}": [
            r"(?<=[集期话部篇第])[上中下一二三四五六七八九十]",
            r"[上中下一二三四五六七八九十]",
        ],
        "{VER}": [r"[\u4e00-\u9fa5]+版"],
    }

    priority_list = [
        "上",
        "中",
        "下",
        "一",
        "二",
        "三",
        "四",
        "五",
        "六",
        "七",
        "八",
        "九",
        "十",
        "百",
        "千",
        "万",
    ]

    def __init__(self, magic_regex={}, magic_variable={}):
        self.magic_regex.update(magic_regex)
        self.magic_variable.update(magic_variable)
        self.dir_filename_dict = {}

    def set_taskname(self, taskname):
        """设置任务名称"""
        self.magic_variable["{TASKNAME}"] = taskname

    def magic_regex_conv(self, pattern, replace):
        """魔法正则匹配"""
        keyword = pattern
        if keyword in self.magic_regex:
            pattern = self.magic_regex[keyword]["pattern"]
            if replace == "":
                replace = self.magic_regex[keyword]["replace"]
        return pattern, replace

    def sub(self, pattern, replace, file_name):
        """魔法正则、变量替换"""
        if not replace:
            return file_name
        # 预处理替换变量
        for key, p_list in self.magic_variable.items():
            if key in replace:
                # 正则类替换变量
                if p_list and isinstance(p_list, list):
                    for p in p_list:
                        match = re.search(p, file_name)
                        if match:
                            # 匹配成功，替换为匹配到的值
                            value = match.group()
                            # 日期格式处理：补全、格式化
                            if key == "{DATE}":
                                value = "".join(
                                    [char for char in value if char.isdigit()]
                                )
                                value = (
                                        str(datetime.now().year)[: (8 - len(value))] + value
                                )
                            replace = replace.replace(key, value)
                            break
                # 非正则类替换变量
                if key == "{TASKNAME}":
                    replace = replace.replace(key, self.magic_variable["{TASKNAME}"])
                elif key == "{SXX}" and not match:
                    replace = replace.replace(key, "S01")
                elif key == "{I}":
                    continue
                else:
                    # 清理未匹配的 magic_variable key
                    replace = replace.replace(key, "")
        if pattern and replace:
            file_name = re.sub(pattern, replace, file_name)
        else:
            file_name = replace
        return file_name

    def _custom_sort_key(self, name):
        """自定义排序键"""
        for i, keyword in enumerate(self.priority_list):
            if keyword in name:
                name = name.replace(keyword, f"_{i:02d}_")  # 替换为数字，方便排序
        return name

    def sort_file_list(self, file_list, dir_filename_dict={}):
        """文件列表统一排序，给{I+}赋值"""
        filename_list = [
            # 强制加入`文件修改时间`字段供排序，效果：1无可排序字符时则按修改时间排序，2和目录已有文件重名时始终在其后
            f"{f['file_name_re']}_{f['updated_at']}"
            for f in file_list
            if f.get("file_name_re") and not f["dir"]
        ]
        # print(f"filename_list_before: {filename_list}")
        dir_filename_dict = dir_filename_dict or self.dir_filename_dict
        # print(f"dir_filename_list: {dir_filename_list}")
        # 合并目录文件列表
        filename_list = list(set(filename_list) | set(dir_filename_dict.values()))
        filename_list = natsorted(filename_list, key=self._custom_sort_key)
        filename_index = {}
        for name in filename_list:
            if name in dir_filename_dict.values():
                continue
            i = filename_list.index(name) + 1
            while i in dir_filename_dict.keys():
                i += 1
            dir_filename_dict[i] = name
            filename_index[name] = i
        for file in file_list:
            if file.get("file_name_re"):
                if match := re.search(r"\{I+\}", file["file_name_re"]):
                    i = filename_index.get(
                        f"{file['file_name_re']}_{file['updated_at']}", 0
                    )
                    file["file_name_re"] = re.sub(
                        match.group(),
                        str(i).zfill(match.group().count("I")),
                        file["file_name_re"],
                    )

    def set_dir_file_list(self, file_list, replace):
        """设置目录文件列表"""
        self.dir_filename_dict = {}
        filename_list = [f["file_name"] for f in file_list if not f["dir"]]
        filename_list.sort()
        if not filename_list:
            return
        if match := re.search(r"\{I+\}", replace):
            # 由替换式转换匹配式
            magic_i = match.group()
            pattern_i = r"\d" * magic_i.count("I")
            pattern = replace.replace(match.group(), "🔢")
            for key, _ in self.magic_variable.items():
                if key in pattern:
                    pattern = pattern.replace(key, "🔣")
            pattern = re.sub(r"\\[0-9]+", "🔣", pattern)  # \1 \2 \3
            pattern = f"({re.escape(pattern).replace('🔣', '.*?').replace('🔢', f')({pattern_i})(')})"
            # print(f"pattern: {pattern}")
            # 获取起始编号
            if match := re.match(pattern, filename_list[-1]):
                self.magic_variable["{I}"] = int(match.group(2))
            # 目录文件列表
            for filename in filename_list:
                if match := re.match(pattern, filename):
                    self.dir_filename_dict[int(match.group(2))] = (
                            match.group(1) + magic_i + match.group(3)
                    )
            # print(f"filename_list: {self.filename_list}")

    def is_exists(self, filename, filename_list, ignore_ext=False):
        """判断文件是否存在，处理忽略扩展名"""
        # print(f"filename: {filename} filename_list: {filename_list}")
        if ignore_ext:
            filename = os.path.splitext(filename)[0]
            filename_list = [os.path.splitext(f)[0] for f in filename_list]
        # {I+} 模式，用I通配数字序号
        if match := re.search(r"\{I+\}", filename):
            magic_i = match.group()
            pattern_i = r"\d" * magic_i.count("I")
            pattern = re.escape(filename).replace(re.escape(magic_i), pattern_i)
            for filename in filename_list:
                if re.match(pattern, filename):
                    return filename
            return None
        else:
            return filename if filename in filename_list else None


class Quark:
    BASE_URL = "https://drive-pc.quark.cn"
    BASE_URL_APP = "https://drive-m.quark.cn"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) quark-cloud-drive/3.14.2 Chrome/112.0.5615.165 Electron/24.1.3.8 Safari/537.36 Channel/pckk_other_ch"

    def __init__(self, cookie="", index=0):
        self.cookie = cookie.strip()
        self.index = index + 1
        self.is_active = False
        self.nickname = ""
        self.mparam = self._match_mparam_form_cookie(cookie)
        self.savepath_fid = {"/": "0"}


    def _generate_random_string(self, length=5):
        """
            生成指定长度的随机字符串，默认为5位数。

            Args:
                length (int): 字符串长度，默认为5

            Returns:
                str: 随机生成的字符串
            """
        # 定义字符集，包括数字和字母
        characters = string.ascii_letters + string.digits
        # 从字符集中随机选择指定数量的字符并组合成字符串
        return ''.join(random.choice(characters) for _ in range(length))


    def _match_mparam_form_cookie(self, cookie):
        mparam = {}
        kps_match = re.search(r"(?<!\w)kps=([a-zA-Z0-9%+/=]+)[;&]?", cookie)
        sign_match = re.search(r"(?<!\w)sign=([a-zA-Z0-9%+/=]+)[;&]?", cookie)
        vcode_match = re.search(r"(?<!\w)vcode=([a-zA-Z0-9%+/=]+)[;&]?", cookie)
        if kps_match and sign_match and vcode_match:
            mparam = {
                "kps": kps_match.group(1).replace("%25", "%"),
                "sign": sign_match.group(1).replace("%25", "%"),
                "vcode": vcode_match.group(1).replace("%25", "%"),
            }
        return mparam

    def _send_request(self, method, url, **kwargs):
        headers = {
            "cookie": self.cookie,
            "content-type": "application/json",
            "user-agent": self.USER_AGENT,
        }
        if "headers" in kwargs:
            headers = kwargs["headers"]
            del kwargs["headers"]
        if self.mparam and "share" in url and self.BASE_URL in url:
            url = url.replace(self.BASE_URL, self.BASE_URL_APP)
            kwargs["params"].update(
                {
                    "device_model": "M2011K2C",
                    "entry": "default_clouddrive",
                    "_t_group": "0%3A_s_vp%3A1",
                    "dmn": "Mi%2B11",
                    "fr": "android",
                    "pf": "3300",
                    "bi": "35937",
                    "ve": "7.4.5.680",
                    "ss": "411x875",
                    "mi": "M2011K2C",
                    "nt": "5",
                    "nw": "0",
                    "kt": "4",
                    "pr": "ucpro",
                    "sv": "release",
                    "dt": "phone",
                    "data_from": "ucapi",
                    "kps": self.mparam.get("kps"),
                    "sign": self.mparam.get("sign"),
                    "vcode": self.mparam.get("vcode"),
                    "app": "clouddrive",
                    "kkkk": "1",
                }
            )
            del headers["cookie"]
        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            # print(f"{response.text}")
            # response.raise_for_status()  # 检查请求是否成功，但返回非200也会抛出异常
            return response
        except Exception as e:
            print(f"_send_request error:\n{e}")
            fake_response = requests.Response()
            fake_response.status_code = 500
            fake_response._content = (
                b'{"status": 500, "code": 1, "message": "request error"}'
            )
            return fake_response

    def init(self):
        account_info = self.get_account_info()
        if account_info:
            self.is_active = True
            self.nickname = account_info["nickname"]
            return account_info
        else:
            return False

    def get_account_info(self):
        """获取账户信息"""
        url = "https://pan.quark.cn/account/info"
        querystring = {"fr": "pc", "platform": "pc"}
        response = self._send_request("GET", url, params=querystring).json()
        if response.get("data"):
            print(f"get_account_info 返回的结果是{response["data"]}")
            return response["data"]
        else:
            return False

    def get_growth_info(self):
        url = f"{self.BASE_URL_APP}/1/clouddrive/capacity/growth/info"
        querystring = {
            "pr": "ucpro",
            "fr": "android",
            "kps": self.mparam.get("kps"),
            "sign": self.mparam.get("sign"),
            "vcode": self.mparam.get("vcode"),
        }
        headers = {
            "content-type": "application/json",
        }
        response = self._send_request(
            "GET", url, headers=headers, params=querystring
        ).json()
        if response.get("data"):
            print(f"get_growth_info 获取到的数据是{response['data']}")
            return response["data"]
        else:
            return False

    def get_growth_sign(self):
        url = f"{self.BASE_URL_APP}/1/clouddrive/capacity/growth/sign"
        querystring = {
            "pr": "ucpro",
            "fr": "android",
            "kps": self.mparam.get("kps"),
            "sign": self.mparam.get("sign"),
            "vcode": self.mparam.get("vcode"),
        }
        payload = {
            "sign_cyclic": True,
        }
        headers = {
            "content-type": "application/json",
        }
        response = self._send_request(
            "POST", url, json=payload, headers=headers, params=querystring
        ).json()
        if response.get("data"):
            print(f"get_growth_sign 返回的数据是{response}")
            return True, response["data"]["sign_daily_reward"]
        else:
            return False, response["message"]

    # 可验证资源是否失效
    def get_stoken(self, pwd_id, passcode=""):
        url = f"{self.BASE_URL}/1/clouddrive/share/sharepage/token"
        querystring = {"pr": "ucpro", "fr": "pc"}
        payload = {"pwd_id": pwd_id, "passcode": passcode}
        response = self._send_request(
            "POST", url, json=payload, params=querystring
        ).json()
        print(f"get_stoken 获取到的数据是{response}")
        return response

    def get_detail(
            self, pwd_id, stoken, pdir_fid, _fetch_share=0, fetch_share_full_path=0
    ):
        list_merge = []
        page = 1
        while True:
            url = f"{self.BASE_URL}/1/clouddrive/share/sharepage/detail"
            querystring = {
                "pr": "ucpro",
                "fr": "pc",
                "pwd_id": pwd_id,
                "stoken": stoken,
                "pdir_fid": pdir_fid,
                "force": "0",
                "_page": page,
                "_size": "50",
                "_fetch_banner": "0",
                "_fetch_share": _fetch_share,
                "_fetch_total": "1",
                "_sort": "file_type:asc,updated_at:desc",
                "ver": "2",
                "fetch_share_full_path": fetch_share_full_path,
            }
            response = self._send_request("GET", url, params=querystring).json()
            print(f"get_detail 获取到的数据是{response}")
            if response["code"] != 0:
                return response
            if response["data"]["list"]:
                list_merge += response["data"]["list"]
                page += 1
            else:
                break
            if len(list_merge) >= response["metadata"]["_total"]:
                break
        response["data"]["list"] = list_merge
        return response

    def get_fids(self, file_paths):
        fids = []
        while True:
            url = f"{self.BASE_URL}/1/clouddrive/file/info/path_list"
            querystring = {"pr": "ucpro", "fr": "pc"}
            payload = {"file_path": file_paths, "namespace": "0"}
            response = self._send_request(
                "POST", url, json=payload, params=querystring
            ).json()
            print(f"get_fids 获取到的数据是{response}")
            if response["code"] == 0:
                fids += response["data"]
                file_paths = file_paths[50:]
            else:
                print(f"获取目录ID：失败, {response['message']}")
                break
            if len(file_paths) == 0:
                break
        return fids

    def ls_dir(self, pdir_fid, **kwargs):
        list_merge = []
        page = 1
        while True:
            url = f"{self.BASE_URL}/1/clouddrive/file/sort"
            querystring = {
                "pr": "ucpro",
                "fr": "pc",
                "uc_param_str": "",
                "pdir_fid": pdir_fid,
                "_page": page,
                "_size": "50",
                "_fetch_total": "1",
                "_fetch_sub_dirs": "0",
                "_sort": "file_type:asc,updated_at:desc",
                "_fetch_full_path": kwargs.get("fetch_full_path", 0),
            }
            response = self._send_request("GET", url, params=querystring).json()
            print(f"ls_dir 获取到的数据是{response}")
            if response["code"] != 0:
                return response
            if response["data"]["list"]:
                list_merge += response["data"]["list"]
                page += 1
            else:
                break
            if len(list_merge) >= response["metadata"]["_total"]:
                break
        response["data"]["list"] = list_merge
        return response

    def share_file_for_taskid(self, fid_list, title):
        url = f"{self.BASE_URL}/1/clouddrive/share"
        querystring = {
            "pr": "ucpro",
            "fr": "pc",
            "uc_param_str": ""
        }
        payload = {
            "fid_list": fid_list,
            "title": title,
            "url_type": 1,
            "expired_type": 1
        }
        response = self._send_request(
            "POST", url, json=payload, params=querystring
        ).json()
        print(f"转存返回的结果 share_file_for_taskid 获取到的数据是： {response}")
        return_res_task_id = response["data"]["task_id"]
        return return_res_task_id

    def share_file(self, share_id):
        url = f"{self.BASE_URL}/1/clouddrive/share/password"
        querystring = {
            "pr": "ucpro",
            "fr": "pc",
            "uc_param_str": ""
        }
        payload = {"share_id": share_id}
        response = self._send_request(
            "POST", url, json=payload, params=querystring
        ).json()
        # 获取分享链接
        print(f"share_file 获取到的数据是{response}")
        share_url = response["data"]["share_url"]
        return share_url

    def save_file(self, fid_list, fid_token_list, to_pdir_fid, pwd_id, stoken):
        url = f"{self.BASE_URL}/1/clouddrive/share/sharepage/save"
        querystring = {
            "pr": "ucpro",
            "fr": "pc",
            "uc_param_str": "",
            "app": "clouddrive",
            "__dt": int(random.uniform(1, 5) * 60 * 1000),
            "__t": datetime.now().timestamp(),
        }
        payload = {
            "fid_list": fid_list,
            "fid_token_list": fid_token_list,
            "to_pdir_fid": to_pdir_fid,
            "pwd_id": pwd_id,
            "stoken": stoken,
            "pdir_fid": "0",
            "scene": "link",
        }
        response = self._send_request(
            "POST", url, json=payload, params=querystring
        ).json()
        print(f"save_file 获取到的数据是{response}")
        return response

    def query_task(self, task_id):
        retry_index = 0
        while True:
            url = f"{self.BASE_URL}/1/clouddrive/task"
            querystring = {
                "pr": "ucpro",
                "fr": "pc",
                "uc_param_str": "",
                "task_id": task_id,
                "retry_index": retry_index,
                "__dt": int(random.uniform(1, 5) * 60 * 1000),
                "__t": datetime.now().timestamp(),
            }
            response = self._send_request("GET", url, params=querystring).json()
            if response["data"]["status"] == 2:
                if retry_index > 0:
                    print()
                break
            else:
                if retry_index == 0:
                    print(
                        f"正在等待[{response['data']['task_title']}]执行结果",
                        end="",
                        flush=True,
                    )
                else:
                    print(".", end="", flush=True)
                retry_index += 1
                time.sleep(0.500)
        print(f"query_task 返回的数据是{response}")
        return response

    def download(self, fids):
        url = f"{self.BASE_URL}/1/clouddrive/file/download"
        querystring = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        payload = {"fids": fids}
        response = self._send_request("POST", url, json=payload, params=querystring)
        set_cookie = response.cookies.get_dict()
        cookie_str = "; ".join([f"{key}={value}" for key, value in set_cookie.items()])
        return response.json(), cookie_str

    def mkdir(self, dir_path):
        url = f"{self.BASE_URL}/1/clouddrive/file"
        querystring = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        payload = {
            "pdir_fid": "0",
            "file_name": "",
            "dir_path": dir_path,
            "dir_init_lock": False,
        }
        response = self._send_request(
            "POST", url, json=payload, params=querystring
        ).json()
        return response

    def rename(self, fid, file_name):
        url = f"{self.BASE_URL}/1/clouddrive/file/rename"
        querystring = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        payload = {"fid": fid, "file_name": file_name}
        response = self._send_request(
            "POST", url, json=payload, params=querystring
        ).json()
        return response

    def delete(self, filelist):
        url = f"{self.BASE_URL}/1/clouddrive/file/delete"
        querystring = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        payload = {"action_type": 2, "filelist": filelist, "exclude_fids": []}
        response = self._send_request(
            "POST", url, json=payload, params=querystring
        ).json()
        return response

    def recycle_list(self, page=1, size=30):
        url = f"{self.BASE_URL}/1/clouddrive/file/recycle/list"
        querystring = {
            "_page": page,
            "_size": size,
            "pr": "ucpro",
            "fr": "pc",
            "uc_param_str": "",
        }
        response = self._send_request("GET", url, params=querystring).json()
        print(f"recycle_list 获取到的数据是{response}")
        return response["data"]["list"]

    def recycle_remove(self, record_list):
        url = f"{self.BASE_URL}/1/clouddrive/file/recycle/remove"
        querystring = {"uc_param_str": "", "fr": "pc", "pr": "ucpro"}
        payload = {
            "select_mode": 2,
            "record_list": record_list,
        }
        response = self._send_request(
            "POST", url, json=payload, params=querystring
        ).json()
        print(f"recycle_remove 获取到的数据是{response}")
        return response

    # ↑ 请求函数
    # ↓ 操作函数

    def extract_url(self, url):
        # pwd_id
        match_id = re.search(r"/s/(\w+)", url)
        pwd_id = match_id.group(1) if match_id else None
        # passcode
        match_pwd = re.search(r"pwd=(\w+)", url)
        passcode = match_pwd.group(1) if match_pwd else ""
        # path: fid-name
        # Legacy 20250905
        paths = []
        matches = re.findall(r"/(\w{32})-?([^/]+)?", url)
        for match in matches:
            fid = match[0]
            name = urllib.parse.unquote(match[1]).replace("*101", "-")
            paths.append({"fid": fid, "name": name})
        pdir_fid = paths[-1]["fid"] if matches else 0
        return pwd_id, passcode, pdir_fid, paths

    def update_savepath_fid(self, tasklist):
        dir_paths = [
            re.sub(r"/{2,}", "/", f"/{item['savepath']}")
            for item in tasklist
            if not item.get("enddate")
               or (
                       datetime.now().date()
                       <= datetime.strptime(item["enddate"], "%Y-%m-%d").date()
               )
        ]
        print(f"dir_paths is {dir_paths}")
        if not dir_paths:
            return False
        dir_paths_exist_arr = self.get_fids(dir_paths)
        dir_paths_exist = [item["file_path"] for item in dir_paths_exist_arr]
        # 比较创建不存在的
        dir_paths_unexist = list(set(dir_paths) - set(dir_paths_exist) - set(["/"]))
        for dir_path in dir_paths_unexist:
            mkdir_return = self.mkdir(dir_path)
            if mkdir_return["code"] == 0:
                new_dir = mkdir_return["data"]
                dir_paths_exist_arr.append(
                    {"file_path": dir_path, "fid": new_dir["fid"]}
                )
                print(f"创建文件夹：{dir_path}")
            else:
                print(f"创建文件夹：{dir_path} 失败, {mkdir_return['message']}")
        # 储存目标目录的fid
        for dir_path in dir_paths_exist_arr:
            self.savepath_fid[dir_path["file_path"]] = dir_path["fid"]
        # print(dir_paths_exist_arr)
        return dir_paths

    def do_save_check(self, shareurl, savepath):
        try:
            pwd_id, passcode, pdir_fid, _ = self.extract_url(shareurl)
            stoken = self.get_stoken(pwd_id, passcode)["data"]["stoken"]
            share_file_list = self.get_detail(pwd_id, stoken, pdir_fid)["data"]["list"]
            print(f"获取分享: {share_file_list}")
            fid_list = [item["fid"] for item in share_file_list]
            fid_token_list = [item["share_fid_token"] for item in share_file_list]
            get_fids = self.get_fids([savepath])
            to_pdir_fid = (
                get_fids[0]["fid"] if get_fids else self.mkdir(savepath)["data"]["fid"]
            )
            save_file = self.save_file(
                fid_list, fid_token_list, to_pdir_fid, pwd_id, stoken
            )
            print(f"转存文件: {save_file}")
            if save_file["code"] == 0:
                task_id = save_file["data"]["task_id"]
                query_task = self.query_task(task_id)
                print(f"查询转存: {query_task}")
                if query_task["code"] == 0:
                    del_list = query_task["data"]["save_as"]["save_as_top_fids"]
                    if del_list:
                        delete_return = self.delete(del_list)
                        print(f"删除转存: {delete_return}")
                        recycle_list = self.recycle_list()
                        record_id_list = [
                            item["record_id"]
                            for item in recycle_list
                            if item["fid"] in del_list
                        ]
                        recycle_remove = self.recycle_remove(record_id_list)
                        print(f"清理转存: {recycle_remove}")
                        print(f"✅ 转存测试成功")
                        return True
            print(f"❌ 转存测试失败: 中断")
            return False
        except Exception as e:
            print(f"❌ 转存测试失败: {str(e)}")
            traceback.print_exc()

    def do_save_task(self, task):
        # 判断资源失效记录
        if task.get("shareurl_ban"):
            print(f"《{task['taskname']}》：{task['shareurl_ban']}")
            return None, task['shareurl_ban']
        # 链接转换所需参数
        pwd_id, passcode, pdir_fid, _ = self.extract_url(task["shareurl"])
        # 获取stoken，同时可验证资源是否失效
        get_stoken = self.get_stoken(pwd_id, passcode)
        if get_stoken.get("status") == 200:
            stoken = get_stoken["data"]["stoken"]
        elif get_stoken.get("status") == 500:
            print(f"跳过任务：网络异常 {get_stoken.get('message')}")
            return None, get_stoken.get("message")
        else:
            message = get_stoken.get("message")
            task["shareurl_ban"] = message
            return None, message
        try:
            updated_tree, tt_flid = self.dir_check_and_save(task, pwd_id, stoken, pdir_fid)
        except Exception as e:
            print(f"❌ 转存失败: {str(e)}")
            return {}, str(e)
        return updated_tree, tt_flid

    def dir_check_and_save(self, task, pwd_id, stoken, pdir_fid="", subdir_path=""):
        ret_dict = {}
        # 获取分享文件列表
        share_file_list = self.get_detail(pwd_id, stoken, pdir_fid)["data"]["list"]
        print("share_file_list: ", share_file_list)
        if not share_file_list:
            if subdir_path == "":
                task["shareurl_ban"] = "分享为空，文件已被分享者删除"
            return {"data":None}, task
        elif (
                len(share_file_list) == 1
                and share_file_list[0]["dir"]
                and subdir_path == ""
        ):  # 仅有一个文件夹
            print("🧠 该分享是一个文件夹，读取文件夹内列表")


        # 获取转存位置的目录文件列表
        savepath = re.sub(r"/{2,}", "/", f"/{task['savepath']}{subdir_path}")
        # 创建一个转存目录，在制定的路径下
        # 生成给随机字符串
        random_str = self._generate_random_string(10)
        fold_name = f"/{savepath}/{random_str}"
        mkdir_return = self.mkdir(fold_name)
        if mkdir_return["code"] == 0:
            new_dir = mkdir_return["data"]
            print(f"创建文件夹：{fold_name} and 返回的结果{new_dir}")
            self.savepath_fid[fold_name] = new_dir["fid"]
        else:
            print(f"❌ 目录 {fold_name} fid获取失败，跳过转存")
            task["shareurl_ban"] = "转存位置目录不存在"
            return  {"data":None},task
        to_pdir_fid = self.savepath_fid[fold_name]
        dir_file_list = self.ls_dir(to_pdir_fid)["data"]["list"]
        dir_filename_list = [dir_file["file_name"] for dir_file in dir_file_list]
        print("dir_file_list: ", dir_file_list)
        print(f"to_pdir_fid is  这个就是转存后存放到夸克网盘的目录ID了，{to_pdir_fid}")
        # 需保存的文件清单
        need_save_list = []
        for item in share_file_list:
            item["file_name_re"] = fold_name
            need_save_list.append(item)
        print(f"need_save_list is {need_save_list}")
        # 转存文件
        fid_list = [item["fid"] for item in need_save_list]
        fid_token_list = [item["share_fid_token"] for item in need_save_list]
        save_as_top_fids = []
        if fid_list:
            err_msg = None
            while fid_list:
                # 分次转存，100个/次，因query_task返回save_as_top_fids最多100
                save_file_return = self.save_file(
                    fid_list[:100], fid_token_list[:100], to_pdir_fid, pwd_id, stoken
                )
                fid_list = fid_list[100:]
                fid_token_list = fid_token_list[100:]
                if save_file_return["code"] == 0:
                    # 转存成功，查询转存结果
                    task_id = save_file_return["data"]["task_id"]
                    query_task_return = self.query_task(task_id)
                    if query_task_return["code"] == 0:
                        save_as_top_fids.extend(
                            query_task_return["data"]["save_as"]["save_as_top_fids"]
                        )
                    else:
                        err_msg = query_task_return["message"]
                else:
                    err_msg = save_file_return["message"]
                if err_msg:
                    print(err_msg)
                    # add_notify(f"❌《{task['taskname']}》转存失败：{err_msg}\n")
        print(f"save_as_top_fids is {save_as_top_fids}")
        #
        for index, item in enumerate(need_save_list):
            # icon = self._get_file_icon(item)
            data = {
                "file_name": item["file_name"],
                "file_name_re": item["file_name_re"],
                "fid": to_pdir_fid,
                "path": f"{item['file_name_re']}",
                "is_dir": item["dir"],
                "obj_category": item.get("obj_category", ""),
            }
            ret_dict["parent_dir_fid"] = pdir_fid
            ret_dict["data"] = data

        print(f"pd_dir is {pdir_fid}")
        return ret_dict, to_pdir_fid

    def _get_file_icon(self, f):
        if f.get("dir"):
            return "📁"
        ico_maps = {
            "video": "🎞️",
            "image": "🖼️",
            "audio": "🎵",
            "doc": "📄",
            "archive": "📦",
            "default": "",
        }
        return ico_maps.get(f.get("obj_category"), "")





    def generate_random_string(self,length=5, include_uppercase=True, include_lowercase=True, include_digits=True,
                               include_symbols=False):
        """
        生成指定长度的随机字符串，支持自定义字符集

        Args:
            length (int): 字符串长度
            include_uppercase (bool): 是否包含大写字母
            include_lowercase (bool): 是否包含小写字母
            include_digits (bool): 是否包含数字
            include_symbols (bool): 是否包含特殊符号

        Returns:
            str: 随机生成的字符串
        """
        characters = ''
        if include_uppercase:
            characters += string.ascii_uppercase
        if include_lowercase:
            characters += string.ascii_lowercase
        if include_digits:
            characters += string.digits
        if include_symbols:
            characters += string.punctuation

        if not characters:
            raise ValueError("至少需要包含一种字符类型")

        return ''.join(random.choice(characters) for _ in range(length))


if __name__ == "__main__":
    pass
