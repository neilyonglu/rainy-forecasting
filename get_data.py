from utils.config_loader import load_config
from api_loader.fileapi_client import run_fileapi
from api_loader.historyapi_client import run_historyapi

if __name__ == "__main__":
    cfg = load_config("config.yaml")
    run_fileapi(cfg, debug=True) # 最新即時雷達圖

    # 合成雷達格點（歷史多時刻）
    # run_historyapi(cfg, debug=True)
