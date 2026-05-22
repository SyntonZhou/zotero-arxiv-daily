import os
import sys
import logging
import time  # 1. 引入 time 库
from omegaconf import DictConfig
import hydra
from loguru import logger
import dotenv
from zotero_arxiv_daily.executor import Executor
import arxiv # 2. 引入 arxiv 库

os.environ["TOKENIZERS_PARALLELISM"] = "false"
dotenv.load_dotenv()

# ==================== 🛠️ 核心频率控制注入 ====================
# arXiv 库内部在调用结果时，默认使用的是 arxiv.Client()
# 我们通过重写它的 initialization，强行把全局的延迟拉长到 5 秒（默认是 3 秒）
# 并且把重试次数提升到 5 次，这样即便偶尔被拒也能自动等待重试。
_original_client_init = arxiv.Client.__init__

def secure_client_init(self, *args, **kwargs):
    kwargs['delay_seconds'] = max(kwargs.get('delay_seconds', 0), 5.0)
    kwargs['num_retries'] = max(kwargs.get('num_retries', 0), 5)
    _original_client_init(self, *args, **kwargs)

arxiv.Client.__init__ = secure_client_init
# ==========================================================

@hydra.main(version_base=None, config_path="../../config", config_name="default")
def main(config:DictConfig):
    # Configure loguru log level based on config
    log_level = "DEBUG" if config.executor.debug else "INFO"
    logger.remove()  # Remove default handler
    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    for logger_name in logging.root.manager.loggerDict:
        if "zotero_arxiv_daily" in logger_name:
            continue
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    if config.executor.debug:
        logger.info("Debug mode is enabled")
    
    executor = Executor(config)
    executor.run()

if __name__ == '__main__':
    main()
