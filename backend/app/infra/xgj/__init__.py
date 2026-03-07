"""闲管家 API 客户端包。"""

from .erp_client import XGJErpClient
from .virtual_client import XGJVirtualClient

__all__ = ["XGJErpClient", "XGJVirtualClient"]
