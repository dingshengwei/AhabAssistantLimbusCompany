import os
import subprocess
import webbrowser
from time import sleep, time

import psutil

from module.config import cfg
from module.platform import IS_MACOS
from utils.singletonmeta import SingletonMeta


class Game(metaclass=SingletonMeta):
    def __init__(self, logger):
        self.game_path = cfg.game_path
        self.game_url = "steam://rungameid/1973530"
        self.log = logger
        self.process_name = cfg.game_process_name
        self.game_path_exists = True
        self.last_check_time = None
        self.check_in_short_time = 0

    def check_game_alive(self):
        for proc in psutil.process_iter(["name"]):
            try:
                # 获取进程的可执行文件名（如 "notepad.exe"）
                proc_name = proc.info["name"]
                # 精确匹配进程名（区分大小写，取决于系统）
                if self.process_name in proc_name:
                    self.log.debug(f"游戏已启动：{self.process_name}，进程ID：{proc.pid}")
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # 忽略已终止、无权限或僵尸进程
                continue
        return False

    def _start_game_macos(self) -> bool:
        """macOS：通过 open 启动 PlayCover 版应用或 MuMu Pro 模拟器。"""
        candidates = [
            self.game_path,
            "LimbusCompany",
            "Limbus Company",
            "MuMu Pro",
            "MuMu模拟器 Pro",
            "MuMu Player Pro",
        ]
        for name in candidates:
            if not name:
                continue
            try:
                proc = subprocess.run(["open", "-a", name], capture_output=True, timeout=20)
            except Exception as exc:
                self.log.debug(f"尝试启动 {name} 失败: {exc}")
                continue
            if proc.returncode == 0:
                self.log.info(f"已启动：{name}")
                sleep(5)
                return True
            self.log.debug(f"open -a {name} 失败: {proc.stderr.decode(errors='ignore').strip()}")
        self.log.error(
            "macOS 上未能启动游戏：请安装 MuMu Pro 模拟器或 PlayCover 版 Limbus Company，"
            "也可以在设置里手动填写游戏路径"
        )
        return False

    def start_game(self) -> bool:
        """启动游戏"""
        if IS_MACOS:
            return self._start_game_macos()
        if self.check_game_alive():
            if self.last_check_time is None or time() - self.last_check_time > 60:
                self.last_check_time = time()
                self.check_in_short_time = 0
            else:
                self.check_in_short_time += 1
            if self.check_in_short_time > 5:
                from tasks.base.retry import kill_game

                kill_game()
                self.check_in_short_time = 0
            else:
                return True

        if not os.path.exists(self.game_path):
            self.log.error(f"游戏路径不存在：{self.game_path}，使用steam命令启动...")
            self.game_path_exists = False

        try:
            # 调用系统打开该 URL（会触发 Steam 启动游戏）
            webbrowser.open(self.game_url)
            self.log.info("使用steam命令启动游戏")
            sleep(5)
            if not self.check_game_alive() and self.game_path_exists:
                os.startfile(self.game_path)
                self.log.info(f"游戏启动：{self.game_path}")
            return True
        except Exception as e:
            self.log.error(f"启动游戏时发生错误：{e}")
        return False
