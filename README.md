# ❄️ Yukinoaaa Trading Assistant

[![Python 3.13+](https://img.shields.io/badge/Python-3.13%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Architecture: Clean & DDD](https://img.shields.io/badge/Architecture-Clean%20%7C%20DDD%20%7C%20EDA-blueviolet?style=for-the-badge)](https://github.com/ayamiko/Yukinoaaa)
[![Docker Ready](https://img.shields.io/badge/Docker-Production%20Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Zero Dependency HTTP](https://img.shields.io/badge/API%20Gateway-Zero%20Dependency-00C7B7?style=for-the-badge)](https://docs.python.org/3/library/asyncio.html)

> **An AI-First, Domain-Driven, and Event-Driven Trading Assistant Platform designed for real-time market analytics, automated risk management, and seamless Discord integration.**

---

## 🌟 Giới Thiệu (Overview)

**Yukinoaaa** không chỉ là một bot giao dịch thông thường. Đây là một **Nền tảng Hỗ trợ Giao dịch & Phân tích Thị trường thế hệ mới**, được xây dựng với mục tiêu đạt độ ổn định tối đa, tốc độ xử lý thời gian thực (< 50ms) và duy trì một kiến trúc sạch, siêu nhẹ theo triết lý **Zero-External-HTTP-Dependency**.

Hệ thống được thiết kế để kết hợp hoàn hảo giữa các chiến lược giao dịch tự toán (Algorithmic Trading), cơ chế quản trị rủi ro nghiêm ngặt (Built-in Risk Engine) và khả năng tương tác linh hoạt với người dùng thông qua **AI Assistant** và **Discord Bot**.

---

## ✨ Tính Năng Nổi Bật (Key Features)

* 🏛️ **Clean Architecture & Domain-Driven Design (DDD):** Hệ thống được phân tách thành 7 tầng kiến trúc độc lập (Domain, Application, Infrastructure, Presentation, Risk, Indicators, Backtest), cô lập hoàn toàn logic kinh doanh khỏi các phụ thuộc kỹ thuật bên ngoài.
* ⚡ **Real-Time Event-Driven Streaming:** Tích hợp bộ điều hướng sự kiện bất đồng bộ (`AsyncEventBus`) với độ trễ dưới 50ms. Tự động chuẩn hóa và phát sóng trực tiếp các dữ liệu Tick, Candlestick (Kline) và trạng thái lệnh qua **Server-Sent Events (SSE)**.
* 🛡️ **Built-in Risk Management Engine:** Hệ thống bảo vệ tài khoản tự động, tự động từ chối tín hiệu giao dịch nếu vi phạm mức sụt giảm tài khoản tối đa (Max Drawdown), giới hạn thua lỗ trong ngày (Daily Loss Ceiling) hoặc sai lệch định cỡ vị thế (Position Sizing).
* 🚀 **Zero-Dependency API Gateway:** Máy chủ HTTP REST & SSE tối giản được xây dựng trực tiếp trên thư viện chuẩn `asyncio.start_server` của Python 3.13, loại bỏ hoàn toàn sự phụ thuộc vào các framework cồng kềnh như FastAPI hay Uvicorn.
* 🤖 **AI & Discord Bot Ready:** Kiến trúc mở cho phép dễ dàng tích hợp các trợ lý AI phân tích thị trường và kết nối thông báo / điều khiển 2 chiều với các bot Discord theo thời gian thực.
* 🐳 **Production-Ready & Containerized:** Đóng gói chuẩn Multi-stage Docker Build siêu nhẹ, đi kèm bộ nhớ đệm tốc độ cao Redis cùng cơ chế **In-Memory Fallback** tự động chuyển đổi khi mất kết nối mạng.

---

## 🏗️ Kiến Trúc Hệ Thống (Architecture Highlights)

Yukinoaaa tuân thủ triết lý Dependency Rule, mọi phụ thuộc đều hướng từ các tầng hạ tầng bên ngoài vào trung tâm cốt lõi (Domain):

```text
+-----------------------------------------------------------------------+
|                    PRESENTATION LAYER (API / Web / Discord)           |
+-----------------------------------------------------------------------+
                                   ↓
+-----------------------------------------------------------------------+
|              APPLICATION LAYER (Trading / Market / Risk / Backtest)   |
+-----------------------------------------------------------------------+
                                   ↓
+-----------------------------------------------------------------------+
|              DOMAIN LAYER (Models / Events / Core Rules / Aggregate)  |
+-----------------------------------------------------------------------+
                                   ↑
+-----------------------------------------------------------------------+
|              INFRASTRUCTURE LAYER (Redis / SQLite / Mock Exchange)    |
+-----------------------------------------------------------------------+
```

---

## 🚀 Khởi Chạy Nhanh (Quick Start)

### 1. Khởi Chạy với Docker Compose (Khuyến nghị cho Production)
Cách nhanh nhất để triển khai toàn bộ hệ thống (bao gồm Redis Cache và Core Orchestrator):

```bash
# Clone repository
git clone https://github.com/ayamiko/Yukinoaaa.git
cd Yukinoaaa

# Build và khởi chạy ngầm bằng Docker Compose
docker compose up --build -d

# Kiểm tra trạng thái hệ thống
curl http://localhost:8000/api/v1/health
```

### 2. Khởi Chạy trong Môi Trường Phát Triển (Local Development)
Yêu cầu hệ thống đã cài đặt **Python 3.13+** và **Redis**:

```bash
# Tạo và kích hoạt môi trường ảo
python3 -m venv .venv
source .venv/bin/activate

# Cài đặt gói ứng dụng
pip install -e ".[dev]"

# Khởi chạy Master Orchestrator
python -m yukinoaaa
```

---

## 📡 Giao Tiếp Thời Gian Thực (SSE Streaming)

Sau khi khởi chạy ứng dụng, bạn có thể kết nối ngay lập tức với luồng sự kiện thời gian thực bằng Pydantic hoặc JavaScript EventSource:

```javascript
const eventSource = new EventSource('http://localhost:8000/api/v1/stream');

eventSource.addEventListener('TickReceived', (event) => {
    const data = JSON.parse(event.data);
    console.log(`[Real-time Tick] ${data.symbol}: $${data.price}`);
});
```

---

## 🤝 Báo Cáo Lỗi & Đóng Góp (Contributing)

Chúng tôi luôn chào đón mọi đóng góp, báo cáo lỗi hoặc đề xuất tính năng mới nhằm hoàn thiện nền tảng. Mọi Pull Request đều cần bảo đảm tuân thủ các quy chuẩn kiến trúc của dự án và vượt qua toàn bộ bộ kiểm thử tự động (`pytest`).

---

## 📄 Bản Quyền (License)

Dự án được phân phối dưới giấy phép [MIT License](LICENSE).  
Copyright (c) 2026 **Ayamiko**.
