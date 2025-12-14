import aiohttp
import asyncio
from utils.yml_utils.yml_operation import YmlOperation
import functools
from typing import Dict, Any, Optional, Union
import os

def config_hot_reload(func):
    """配置热加载装饰器"""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if hasattr(self, "_check_config_update"):
            self._check_config_update()
        return func(self, *args, **kwargs)

    return wrapper


class ZjFuwuQi:
    """
    从自己搭建的服务器中获取百度夸克资源
    """
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=10)
        self.session :Optional[aiohttp.ClientSession] = None
        self.yml_operation = YmlOperation()
        self.config = self.yml_operation.load_config()
        self.config_path = self.yml_operation.config_path
        self.config_mtime = os.path.getmtime(self.config_path)
        self.url = self.config.get('ZJ_FUWU_QI_URL', "ZJ_FUWU_QI_URL")
        self.headers = {"Content-Type": "application/json"}

    def _check_config_update(self):
        """检查配置文件是否更新"""
        current_mtime = os.path.getmtime(self.config_path)
        if current_mtime > self.config_mtime:
            self._reload_config()
            self.config_mtime = current_mtime

    def _reload_config(self):
        """重新加载配置文件"""
        self.yml = YmlOperation()
        self.config = self.yml.load_config()
        self.headers = self.config.get('BAIDU_HEADERS', "BAIDU_HEADERS")
        print("配置文件已重新加载")


    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    async def get_resource(self, url: str = "", params: Optional[Dict] = None,
                           headers: Optional[Dict] = None) -> Union[Dict[str, Any], str]:
        """
        向特定网站获取资源的异步方法

        Args:
            url: 目标网站URL
            params: 查询参数
            headers: 请求头信息

        Returns:
            响应数据（JSON格式字典或文本）
        """
        if not self.session:
            raise RuntimeError("请在异步上下文管理器中使用此方法")

        if not url:
            url = self.url
        if not headers:
            headers = self.headers
        try:
            async with self.session.get(url, params=params, headers=headers) as response:
                # 根据响应内容类型决定返回格式
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    return await response.json()
                else:
                    return await response.text()
        except Exception as e:
            print(f"获取资源失败: {e}")
            raise

    async def post_data(self, url: str=None, data: Optional[Dict] = None,
                        headers: Optional[Dict] = None) -> Union[Dict[str, Any], str]:
        """
        向特定网站发送POST请求

        Args:
            url: 目标网站URL
            data: POST数据
            headers: 请求头信息

        Returns:
            响应数据
        """
        if not self.session:
            raise RuntimeError("请在异步上下文管理器中使用此方法")

        if not url:
            url = self.url

        url = url + "/api/search"
        if not headers:
            headers = self.headers
        # req_data = {}
        # req_data["kw"] = data["kw"]
        # req_data["cloud_types"] = []
        # req_data["cloud_types"].append(data["share_type"])
        try:
            async with self.session.post(url, json=data, headers=headers) as response:
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    return await response.json()
                else:
                    return await response.text()
        except Exception as e:
            print(f"POST请求失败: {e}")
            raise



