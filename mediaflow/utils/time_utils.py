from datetime import datetime
from typing import Optional

class TimeUtils:
    @staticmethod
    def time_difference(last_seen_str: Optional[str]) -> str:

        try:
            if not last_seen_str:
                return ""
            if not isinstance(last_seen_str, str):
                return ""
            last_seen = datetime.strptime(last_seen_str, "%Y-%m-%d %H:%M:%S")
            current_time = datetime.now()

            time_diff = current_time - last_seen

            days = time_diff.days
            hours, remainder = divmod(time_diff.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            result_parts = []
            if days > 0:
                result_parts.append(f"{days}天")
            if hours > 0:
                result_parts.append(f"{hours}时")
            if minutes > 0 or (days == 0 and hours == 0):
                result_parts.append(f"{minutes}分")

            return ''.join(result_parts) + "前"
        except:
            return ''

    @staticmethod
    def less_than_days(date_str: Optional[str], target_days: int) -> bool:
        """
        小于指定天数
        """
        try:
            if not date_str:
                return False
            if not isinstance(date_str, str):
                return False
            last_seen = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            current_time = datetime.now()

            time_diff = current_time - last_seen

            days = time_diff.days

            if days > target_days:
                return False
            else:
                return True
        except:
            return False

