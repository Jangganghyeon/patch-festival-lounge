from __future__ import annotations

import socket
import subprocess
import sys
from pathlib import Path

from lounge.config import load_config

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
    config = load_config()
    print("\nPATCH Festival Lounge")
    print("- 메인 화면    : http://localhost:8501/")
    print(f"- 입장 키오스크: http://{ip}:8501/?view=kiosk")
    print(f"- 실시간 현황판: http://{ip}:8501/?view=board")
    print(f"- 운영자 콘솔  : http://{ip}:8501/?view=admin")
    print(f"- 초기 설정 코드: {config.initial_setup_code}")
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
