#!/bin/sh
set -e

# Tự động đăng ký Discord Slash Commands trước khi khởi chạy ứng dụng
echo "[*] Đang kiểm tra và đăng ký Slash Commands cho Discord Bot..."
python scripts/register_discord_commands.py --auto || true

# Khởi chạy lệnh mặc định hoặc lệnh được truyền vào
exec "$@"
