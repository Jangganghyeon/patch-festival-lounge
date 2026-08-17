from __future__ import annotations

import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def main() -> int:
    ip = local_ip()
    print("\nPATCH Festival Lounge")
    print("- 메인 화면    : http://localhost:8501/")
    print(f"- 입장 키오스크: http://{ip}:8501/?view=kiosk")
    print(f"- 퇴장 처리    : http://{ip}:8501/?view=checkout")
    print(f"- VIP 현황판   : http://{ip}:8501/?view=board&category=vip")
    print(f"- 일반 현황판  : http://{ip}:8501/?view=board&category=general")
    print(f"- 운영자 콘솔  : http://{ip}:8501/?view=admin")
    print(f"- 영업 분석    : http://{ip}:8501/?view=analytics")
    print("\n같은 와이파이에 연결된 기기에서 위 주소를 여세요. 종료는 Ctrl+C입니다.\n")
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app.py",
            "--server.address=0.0.0.0",
            "--server.port=8501",
        ],
        cwd=ROOT,
    )


if __name__ == "__main__":
    raise SystemExit(main())
