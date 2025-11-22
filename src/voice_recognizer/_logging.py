from typing import Optional, Union
import yaml
import time

import logging
import logging.config

from functools import wraps
from pathlib import Path

# 将模块名作为根记录器 (注意要与配置中的名称一致)
BASELOG_DOMAIN = "voice_recognizer"
# 基于当前文件检索 log_config.yaml
LOG_CONFIG_ROOT = Path(__file__).parent
# 日志文件夹
using_log_output_root: Optional[Path] = None

# 仅在主程序调用, 避免重复初始化
def setup_logging(
    log_output_root: Union[Path, str] = LOG_CONFIG_ROOT.joinpath("logs")
):
    if not isinstance(log_output_root, Path):
        log_output_root = Path(log_output_root)
    if not log_output_root.exists():
        log_output_root.mkdir(parents = True)
    global using_log_output_root
    using_log_output_root = log_output_root

    with open(LOG_CONFIG_ROOT.joinpath("log_config.yaml"), encoding = 'utf-8') as f:
        # 使用 pyyaml 模块加载配置, 加载器选择 FullLoader 或 SafeLoader
        conf = yaml.load(f, yaml.FullLoader)

        # 在线修改属性, 使用程序运行时间作为日志名
        time_str = time.strftime("%Y_%m_%d_%H", time.localtime(time.time()))
        conf["handlers"]["file"]["filename"] = log_output_root.joinpath(f"{time_str}.log")

        # 在配置文件中仅设置根记录器, 其下的子记录器的内容能自动传递到根记录器
        logging.config.dictConfig(conf)

def get_log_output_root():
    return using_log_output_root

# 模仿 getLogger, 但使用指定的根记录器
def getLogger(model_name: Optional[str] = None):
    if model_name != None: 
        return logging.getLogger(f"{BASELOG_DOMAIN}.{model_name}")
    else:
        return logging.getLogger(BASELOG_DOMAIN)
    
def log_and_raise(logger):
    """接受 logger 对象的装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Error in {func.__name__}: {e}")
                raise  e# 继续抛出原异常
        return wrapper
    return decorator