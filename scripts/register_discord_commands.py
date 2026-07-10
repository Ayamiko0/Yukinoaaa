#!/usr/bin/env python3
"""Utility script to register Yukinoaaa Slash Commands with Discord REST API (v10)."""

import json
import os
import sys
import urllib.error
import urllib.request


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


def main() -> None:
    """Register all supported Slash Commands to Discord Developer API."""
    load_env_file(".env")
    bot_token = os.environ.get("DISCORD_BOT_TOKEN", "").strip().strip("'\"")
    if bot_token.lower().startswith("bot "):
        bot_token = bot_token[4:].strip()
    app_id = os.environ.get("DISCORD_APPLICATION_ID", "").strip().strip("'\"")

    if not bot_token or not app_id:
        print("====== YUKINOAAA DISCORD SLASH COMMAND REGISTRAR ======")
        print("Vui lòng điền DISCORD_APPLICATION_ID và DISCORD_BOT_TOKEN vào file .env")
        print("Hoặc chạy trực tiếp qua biến môi trường:")
        print(
            "  DISCORD_APPLICATION_ID=<Client_ID> DISCORD_BOT_TOKEN=<Bot_Token> python3 scripts/register_discord_commands.py"
        )
        print("=========================================================")
        sys.exit(1)

    url = f"https://discord.com/api/v10/applications/{app_id}/commands"

    commands = [
        {
            "name": "help",
            "description": "Hiển thị danh sách các lệnh hỗ trợ của Yukinoaaa Trading Assistant",
        },
        {
            "name": "status",
            "description": "Kiểm tra tình trạng sức khỏe và kết nối thời gian thực của Yukinoaaa",
        },
        {
            "name": "portfolio",
            "description": "Xem báo cáo tổng quan tài khoản giao dịch thời gian thực",
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
        },
    ]

    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json",
        "User-Agent": "DiscordBot (https://github.com/ayamiko0/Yukinoaaa, 0.1.0)",
    }

    print(
        f"[*] Đang đăng ký {len(commands)} lệnh Slash Command tới Discord Application ID: {app_id}..."
    )
    req = urllib.request.Request(
        url, data=json.dumps(commands).encode("utf-8"), headers=headers, method="PUT"
    )

    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            print("[+] THÀNH CÔNG! Đã đăng ký các lệnh sau lên Discord:")
            for cmd in res_data:
                print(f"    - /{cmd.get('name')}: {cmd.get('description')}")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        print(f"[-] LỖI HTTP {e.code}: {err_body}")
        sys.exit(1)
    except Exception as e:
        print(f"[-] LỖI KẾT NỐI: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
