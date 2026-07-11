import os
import sys
import platform
import subprocess
import plistlib
from datetime import datetime


# ==============================
# 基本路徑設定
# ==============================
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DAILY_UPDATE_SCRIPT = os.path.join(PROJECT_ROOT, "daily_update.py")

LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

SCHEDULER_LOG = os.path.join(LOG_DIR, "scheduler_setup_log.txt")

TASK_NAME = "YahooStockAnalysisDailyUpdate"
MAC_PLIST_NAME = "com.yahoo.stock.analysis.dailyupdate.plist"


# ==============================
# 工具函式
# ==============================
def log(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = f"[{now}] {message}"
    print(text)

    with open(SCHEDULER_LOG, "a", encoding="utf-8") as f:
        f.write(text + "\n")


def check_daily_update_exists():
    if not os.path.exists(DAILY_UPDATE_SCRIPT):
        raise FileNotFoundError(f"找不到 daily_update.py：{DAILY_UPDATE_SCRIPT}")


def parse_time(time_text):
    """
    將 HH:MM 轉成 hour, minute
    """
    try:
        hour_text, minute_text = time_text.split(":")
        hour = int(hour_text)
        minute = int(minute_text)

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError

        return hour, minute

    except Exception:
        raise ValueError("時間格式錯誤，請使用 HH:MM，例如 18:30")


def get_python_path():
    """
    使用目前虛擬環境的 Python
    """
    return sys.executable


# ==============================
# Mac：launchd
# ==============================
def install_mac_launchd(time_text):
    hour, minute = parse_time(time_text)

    python_path = get_python_path()

    launch_agents_dir = os.path.expanduser("~/Library/LaunchAgents")
    os.makedirs(launch_agents_dir, exist_ok=True)

    plist_path = os.path.join(launch_agents_dir, MAC_PLIST_NAME)

    stdout_log = os.path.join(LOG_DIR, "daily_update_stdout.log")
    stderr_log = os.path.join(LOG_DIR, "daily_update_stderr.log")

    plist_data = {
        "Label": "com.yahoo.stock.analysis.dailyupdate",
        "ProgramArguments": [
            python_path,
            DAILY_UPDATE_SCRIPT
        ],
        "WorkingDirectory": PROJECT_ROOT,
        "StartCalendarInterval": {
            "Hour": hour,
            "Minute": minute
        },
        "StandardOutPath": stdout_log,
        "StandardErrorPath": stderr_log,
        "RunAtLoad": False
    }

    with open(plist_path, "wb") as f:
        plistlib.dump(plist_data, f)

    log(f"已建立 Mac launchd plist：{plist_path}")

    # 先嘗試卸載舊排程，避免重複
    subprocess.run(
        ["launchctl", "unload", plist_path],
        capture_output=True,
        text=True
    )

    result = subprocess.run(
        ["launchctl", "load", plist_path],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        log("Mac 每日自動更新排程安裝成功")
        log(f"每日執行時間：{time_text}")
        log(f"Python：{python_path}")
        log(f"執行程式：{DAILY_UPDATE_SCRIPT}")
    else:
        log("Mac 排程安裝可能失敗")
        log(result.stderr)
        raise RuntimeError(result.stderr)


def uninstall_mac_launchd():
    plist_path = os.path.expanduser(f"~/Library/LaunchAgents/{MAC_PLIST_NAME}")

    if os.path.exists(plist_path):
        subprocess.run(
            ["launchctl", "unload", plist_path],
            capture_output=True,
            text=True
        )

        os.remove(plist_path)
        log(f"已移除 Mac 排程：{plist_path}")
    else:
        log("找不到 Mac 排程檔，可能尚未安裝")


# ==============================
# Windows：工作排程器
# ==============================
def install_windows_task(time_text):
    parse_time(time_text)

    python_path = get_python_path()

    task_command = f'"{python_path}" "{DAILY_UPDATE_SCRIPT}"'

    result = subprocess.run(
        [
            "schtasks",
            "/Create",
            "/SC", "DAILY",
            "/TN", TASK_NAME,
            "/TR", task_command,
            "/ST", time_text,
            "/F"
        ],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        log("Windows 工作排程安裝成功")
        log(f"每日執行時間：{time_text}")
    else:
        log("Windows 工作排程安裝失敗")
        log(result.stderr)
        raise RuntimeError(result.stderr)


def uninstall_windows_task():
    result = subprocess.run(
        [
            "schtasks",
            "/Delete",
            "/TN", TASK_NAME,
            "/F"
        ],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        log("Windows 工作排程已移除")
    else:
        log("Windows 工作排程移除失敗或不存在")
        log(result.stderr)


# ==============================
# Linux：cron
# ==============================
def install_linux_cron(time_text):
    hour, minute = parse_time(time_text)

    python_path = get_python_path()

    cron_line = (
        f'{minute} {hour} * * * cd "{PROJECT_ROOT}" && '
        f'"{python_path}" "{DAILY_UPDATE_SCRIPT}" '
        f'>> "{os.path.join(LOG_DIR, "daily_update_cron.log")}" 2>&1 '
        f'# {TASK_NAME}'
    )

    current_cron_result = subprocess.run(
        ["crontab", "-l"],
        capture_output=True,
        text=True
    )

    current_cron = current_cron_result.stdout if current_cron_result.returncode == 0 else ""

    # 移除舊的同名排程
    new_lines = [
        line for line in current_cron.splitlines()
        if TASK_NAME not in line
    ]

    new_lines.append(cron_line)

    new_cron = "\n".join(new_lines) + "\n"

    result = subprocess.run(
        ["crontab", "-"],
        input=new_cron,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        log("Linux cron 每日排程安裝成功")
        log(f"每日執行時間：{time_text}")
    else:
        log("Linux cron 安裝失敗")
        log(result.stderr)
        raise RuntimeError(result.stderr)


def uninstall_linux_cron():
    current_cron_result = subprocess.run(
        ["crontab", "-l"],
        capture_output=True,
        text=True
    )

    current_cron = current_cron_result.stdout if current_cron_result.returncode == 0 else ""

    new_lines = [
        line for line in current_cron.splitlines()
        if TASK_NAME not in line
    ]

    new_cron = "\n".join(new_lines) + "\n"

    result = subprocess.run(
        ["crontab", "-"],
        input=new_cron,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        log("Linux cron 排程已移除")
    else:
        log("Linux cron 排程移除失敗")
        log(result.stderr)


# ==============================
# 依照系統安裝 / 移除
# ==============================
def install_scheduler(time_text):
    check_daily_update_exists()

    system_name = platform.system()

    log("=" * 60)
    log("開始設定每日自動更新排程")
    log(f"偵測到系統：{system_name}")
    log(f"專案路徑：{PROJECT_ROOT}")
    log(f"daily_update.py：{DAILY_UPDATE_SCRIPT}")
    log(f"預計每日執行時間：{time_text}")

    if system_name == "Darwin":
        install_mac_launchd(time_text)
    elif system_name == "Windows":
        install_windows_task(time_text)
    elif system_name == "Linux":
        install_linux_cron(time_text)
    else:
        raise RuntimeError(f"目前不支援此系統：{system_name}")


def uninstall_scheduler():
    system_name = platform.system()

    log("=" * 60)
    log("開始移除每日自動更新排程")
    log(f"偵測到系統：{system_name}")

    if system_name == "Darwin":
        uninstall_mac_launchd()
    elif system_name == "Windows":
        uninstall_windows_task()
    elif system_name == "Linux":
        uninstall_linux_cron()
    else:
        raise RuntimeError(f"目前不支援此系統：{system_name}")


def show_status():
    system_name = platform.system()

    print("\n=== Yahoo 股票分析系統：排程設定狀態 ===")
    print(f"目前系統：{system_name}")
    print(f"專案路徑：{PROJECT_ROOT}")
    print(f"Python 路徑：{get_python_path()}")
    print(f"daily_update.py：{DAILY_UPDATE_SCRIPT}")
    print(f"排程名稱：{TASK_NAME}")

    if system_name == "Darwin":
        plist_path = os.path.expanduser(f"~/Library/LaunchAgents/{MAC_PLIST_NAME}")
        print(f"Mac plist：{plist_path}")
        print(f"plist 是否存在：{os.path.exists(plist_path)}")

    print("=====================================\n")


# ==============================
# 執行入口
# ==============================
if __name__ == "__main__":
    args = sys.argv[1:]

    if "--uninstall" in args:
        uninstall_scheduler()

    elif "--status" in args:
        show_status()

    else:
        time_text = "18:30"

        if "--time" in args:
            index = args.index("--time")
            try:
                time_text = args[index + 1]
            except IndexError:
                raise ValueError("請在 --time 後面輸入時間，例如 --time 18:30")

        install_scheduler(time_text)