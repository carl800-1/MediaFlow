import json
from typing import Any, Dict, Union, Optional

from app.helper import DictHelper
from app.utils.commons import singleton
from app.utils.types import SystemConfigKey


@singleton
class SystemConfig:
    systemconfig: Dict[str, Any]

    def __init__(self):
        self.dicthelper = DictHelper()
        self.init_config()

    def init_config(self) -> None:
        """
        缓存系统设置
        """
        for item in self.dicthelper.list("SystemConfig"):
            if not item:
                continue
            if self.__is_obj(item.VALUE):
                self.systemconfig[item.KEY] = json.loads(item.VALUE)
            else:
                self.systemconfig[item.KEY] = item.VALUE

    @staticmethod
    def __is_obj(obj: Any) -> bool:
        if isinstance(obj, list) or isinstance(obj, dict):
            return True
        else:
            return str(obj).startswith("{") or str(obj).startswith("[")

    def set(self, key: Union[SystemConfigKey, str], value: Any) -> None:
        """
        设置系统设置
        """
        if isinstance(key, SystemConfigKey):
            key = key.value
        self.systemconfig[key] = value
        if self.__is_obj(value):
            if value is not None:
                value = json.dumps(value)
            else:
                value = ''
        self.dicthelper.set("SystemConfig", key, value)

    def get(self, key: Optional[Union[SystemConfigKey, str]] = None) -> Any:
        """
        获取系统设置
        """
        if not key:
            return self.systemconfig
        if isinstance(key, SystemConfigKey):
            key = key.value
        return self.systemconfig.get(key)
