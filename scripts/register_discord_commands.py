#!/usr/bin/env python3
"""Utility script to register Yukinoaaa Slash Commands with Discord REST API (v10)."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


def load_env_file(env_path: str = ".env") -> None:
    """Load configuration variables from .env file into os.environ if present."""
    if not os.path.exists(env_path):
        return
    print(f"[*] Đang đọc biến môi trường từ file {env_path}...")
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            if key and not os.environ.get(key):
                os.environ[key] = val


def get_commands_payload() -> list[dict[str, Any]]:
    """Return Discord API v10 command definitions including integration_types and contexts."""
    # integration_types: 0 = GUILD_INSTALL, 1 = USER_INSTALL
    # contexts: 0 = GUILD, 1 = BOT_DM, 2 = PRIVATE_CHANNEL
    common_meta = {
        "integration_types": [0, 1],
        "contexts": [0, 1, 2],
    }

    return [
        {
            "name": "help",
            "description": "Hiển thị danh sách các lệnh hỗ trợ của Yukinoaaa Trading Assistant",
            **common_meta,
        },
        {
            "name": "status",
            "description": "Kiểm tra tình trạng sức khỏe và kết nối thời gian thực của Yukinoaaa",
            **common_meta,
        },
        {
            "name": "portfolio",
            "description": "Xem báo cáo tổng quan tài khoản giao dịch thời gian thực",
            **common_meta,
        },
        {
            "name": "price",
            "description": "Tra cứu giá thị trường và tín hiệu kỹ thuật của cặp tiền",
            "options": [
                {
                    "name": "symbol",
                    "description": "Cặp tiền giao dịch (Ví dụ: BTC/USDT, ETH/USDT)",
                    "type": 3,  # STRING
                    "required": False,
                }
            ],
            **common_meta,
        },
        {
            "name": "backtest",
            "description": "Chạy mô phỏng định lượng Backtest cho chiến lược giao dịch",
            "options": [
                {
                    "name": "symbol",
                    "description": "Cặp tiền giao dịch (Ví dụ: BTC/USDT)",
                    "type": 3,  # STRING
                    "required": False,
                }
            ],
            **common_meta,
        },
        {
            "name": "ai",
            "description": "Phân tích định lượng thị trường bằng Local LLM (Ollama)",
            "options": [
                {
                    "name": "symbol",
                    "description": "Cặp tiền giao dịch (Ví dụ: BTC/USDT)",
                    "type": 3,  # STRING
                    "required": False,
                }
            ],
            **common_meta,
        },
        {
            "name": "analyze",
            "description": "Phân tích định lượng thị trường bằng Local LLM (Ollama)",
            "options": [
                {
                    "name": "symbol",
                    "description": "Cặp tiền giao dịch (Ví dụ: BTC/USDT)",
                    "type": 3,  # STRING
                    "required": False,
                }
            ],
            **common_meta,
        },
    ]


def register_to_endpoint(url: str, headers: dict[str, str], commands: list[dict[str, Any]]) -> bool:
    """Send PUT request to Discord REST API endpoint."""
    req = urllib.request.Request(
        url, data=json.dumps(commands).encode("utf-8"), headers=headers, method="PUT"
    )
    with urllib.request.urlopen(req) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        print("[+] THÀNH CÔNG! Đã đăng ký các lệnh sau lên Discord:")
        for cmd in res_data:
            print(f"    - /{cmd.get('name')}: {cmd.get('description')}")
        return True


def main(soft_fail: bool = False, cli_args: argparse.Namespace | None = None) -> int:
    """Register all supported Slash Commands to Discord Developer API."""
    load_env_file(".env")

    bot_token = (
        (
            getattr(cli_args, "token", None)
            or os.environ.get("DISCORD_BOT_TOKEN")
            or os.environ.get("BOT_TOKEN")
            or ""
        )
        .strip()
        .strip("'\"")
    )
    if bot_token.lower().startswith("bot "):
        bot_token = bot_token[4:].strip()

    app_id = (
        (
            getattr(cli_args, "app_id", None)
            or os.environ.get("DISCORD_APPLICATION_ID")
            or os.environ.get("APPLICATION_ID")
            or ""
        )
        .strip()
        .strip("'\"")
    )

    guild_id = (
        (
            getattr(cli_args, "guild_id", None)
            or os.environ.get("DISCORD_GUILD_ID")
            or os.environ.get("GUILD_ID")
            or ""
        )
        .strip()
        .strip("'\"")
    )

    if not bot_token or not app_id:
        msg = (
            "====== YUKINOAAA DISCORD SLASH COMMAND REGISTRAR ======\n"
            "Chưa cấu hình DISCORD_APPLICATION_ID hoặc DISCORD_BOT_TOKEN.\n"
            "Vui lòng cấu hình trong file .env hoặc truyền qua cờ CLI (--token / --app-id).\n"
            "======================================================="
        )
        print(msg)
        if soft_fail:
            return 0
        return 1

    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json",
        "User-Agent": "DiscordBot (https://github.com/ayamiko0/Yukinoaaa, 0.1.0)",
    }

    commands = get_commands_payload()
    print(
        f"[*] Đang đăng ký {len(commands)} lệnh Slash Command tới Discord Application ID: {app_id}..."
    )

    success = False
    try:
        # Nếu có Guild ID, đăng ký Guild Commands (có hiệu lực NGAY LẬP TỨC không cần chờ 1 giờ)
        if guild_id:
            guild_url = (
                f"https://discord.com/api/v10/applications/{app_id}/guilds/{guild_id}/commands"
            )
            print(f"[*] Đang đăng ký tức thì cho Guild ID: {guild_id}...")
            success = register_to_endpoint(guild_url, headers, commands)

        # Đăng ký Global Commands (phạm vi toàn bộ server & User App)
        global_url = f"https://discord.com/api/v10/applications/{app_id}/commands"
        print("[*] Đang đăng ký Global Slash Commands (áp dụng cho mọi server)...")
        success = register_to_endpoint(global_url, headers, commands) or success

        if success:
            return 0
        return 1
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        print(f"[-] LỖI HTTP {e.code}: {err_body}")
        if soft_fail:
            return 0
        return 1
    except Exception as e:
        print(f"[-] LỖI KẾT NỐI: {str(e)}")
        if soft_fail:
            return 0
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Yukinoaaa Discord Slash Command Registrar")
    parser.add_argument("--token", help="Discord Bot Token", default=None)
    parser.add_argument("--app-id", help="Discord Application ID", default=None)
    parser.add_argument(
        "--guild-id", "-g", help="Discord Guild ID for instant registration", default=None
    )
    parser.add_argument("--auto", "--soft", action="store_true", help="Soft fail on error")
    args = parser.parse_args()

    sys.exit(main(soft_fail=args.auto, cli_args=args))
