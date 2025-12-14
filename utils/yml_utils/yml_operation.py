import yaml
import pathlib

class YmlOperation:
    def __init__(self, config_file = None):
        # 配置文件路径
        config_file = config_file  if config_file else 'config.yml'
        self.config_path = pathlib.Path(__file__).resolve().parent.parent.parent.joinpath(config_file)

    def load_config(self, config_path=None):
        if config_path is None:
            config_path = self.config_path
        with open(config_path, 'r') as stream:
            config = yaml.safe_load(stream)
        return config

    def update_config(self, updates, config_path=None):
        """
        部分更新配置文件，只修改指定的配置项

        Args:
            updates (dict): 需要更新的配置项字典
            config_path (str, optional): 配置文件路径，如果不提供则使用默认路径
        """
        if config_path is None:
            config_path = self.config_path

        # 先加载现有配置
        try:
            existing_config = self.load_config(config_path)
            if existing_config is None:
                existing_config = {}
        except FileNotFoundError:
            existing_config = {}

        # 递归更新配置项
        def deep_update(original, update_data):
            for key, value in update_data.items():
                if isinstance(value, dict) and key in original and isinstance(original[key], dict):
                    deep_update(original[key], value)
                else:
                    original[key] = value

        # 应用更新
        deep_update(existing_config, updates)

        # 写入更新后的配置
        with open(config_path, 'w') as file:
            yaml.dump(existing_config, file, default_flow_style=False, allow_unicode=True)
