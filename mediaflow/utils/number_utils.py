from typing import Union, Optional

class NumberUtils:

    @staticmethod
    def max_ele(a: Optional[Union[int, float]], b: Optional[Union[int, float]]) -> Union[int, float]:
        """
        返回非空最大值
        """
        if not a:
            return b if b is not None else 0
        if not b:
            return a
        return max(int(a), int(b))

    @staticmethod
    def get_size_gb(size: Optional[Union[int, float]]) -> float:
        """
        将字节转换为GB
        """
        if not size:
            return 0.0
        return float(size) / 1024 / 1024 / 1024
