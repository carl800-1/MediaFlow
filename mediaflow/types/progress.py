"""
类型注解进度追踪

用于跟踪项目中类型注解的覆盖率
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class TypeAnnotationProgress:
    """类型注解进度追踪"""
    module_name: str
    total_lines: int = 0
    typed_lines: int = 0
    untyped_functions: list[str] = field(default_factory=list)
    last_updated: Optional[datetime] = None

    @property
    def coverage(self) -> float:
        """计算类型注解覆盖率"""
        if self.total_lines == 0:
            return 0.0
        return round((self.typed_lines / self.total_lines) * 100, 2)

    def update(self, total: int, typed: int, functions: Optional[list[str]] = None) -> None:
        """更新进度"""
        self.total_lines = total
        self.typed_lines = typed
        if functions is not None:
            self.untyped_functions = functions
        self.last_updated = datetime.now()


MODULE_PROGRESS: dict[str, TypeAnnotationProgress] = {}


def get_module_progress(module: str) -> TypeAnnotationProgress:
    """获取模块进度"""
    if module not in MODULE_PROGRESS:
        MODULE_PROGRESS[module] = TypeAnnotationProgress(module_name=module)
    return MODULE_PROGRESS[module]


def get_total_coverage() -> float:
    """获取总体覆盖率"""
    if not MODULE_PROGRESS:
        return 0.0
    total = sum(p.total_lines for p in MODULE_PROGRESS.values())
    typed = sum(p.typed_lines for p in MODULE_PROGRESS.values())
    if total == 0:
        return 0.0
    return round((typed / total) * 100, 2)
