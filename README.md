# PATCH Festival Lounge

학교 축제의 입장, 활동 포인트, 실시간 현황, 퇴장 정산을 한 번에 처리하는 Streamlit 운영 시스템입니다. 카지노풍의 라운지 디자인을 사용하지만 실제 도박이나 배팅 기능은 없으며, 포인트는 구매·환전할 수 없는 학교 축제용 기록 단위입니다.

## 완성된 기능

- 방문자용 입장 키오스크: 이름, 나이, 전화번호, VIP/일반 구분
- 전화번호 기준 중복 입장 방지와 기억하기 쉬운 영문 대문자 2글자 고유 ID 발급
- `RT70` 입력만으로 RT 참가자에게 70포인트를 추가하는 초고속 운영자 입력
- `RT-20` 형식의 정정 차감 및 모든 변경 이력 보존
- 이름, 입장 코드, 전화번호 뒤 4자리 검색
- 퇴장 시 실물 보유 포인트 확인 및 최종값 저장
- 실수로 처리한 퇴장 복구
- 2초 자동 갱신 TOP 3 시상대와 개인정보 보호형 전체 순위표
- 방문자/포인트 이력 CSV 백업
- 전화번호 암호화 저장, 일반 화면 마스킹, 관리자 로그인
- 보관기간이 지난 개인정보의 되돌릴 수 없는 익명화
- SQLite 로컬 운영 및 PostgreSQL 클라우드 운영 지원

## 가장 쉬운 실행 방법 — 학교 현장 권장

행사장 메인 컴퓨터에서 `run_windows.bat`을 더블클릭합니다. 최초 한 번은 패키지 설치로 몇 분이 걸릴 수 있습니다. 실행 창에 다음과 같은 주소가 표시됩니다.

- 메인: `http://localhost:8501/`
- 입장 키오스크: `http://메인컴퓨터IP:8501/?view=kiosk`
- 실시간 현황판: `http://메인컴퓨터IP:8501/?view=board`
- 운영자 콘솔: `http://메인컴퓨터IP:8501/?view=admin`

입장용 컴퓨터와 현황판 컴퓨터를 메인 컴퓨터와 같은 Wi-Fi에 연결한 뒤 해당 주소를 열면 됩니다. 최초 운영자 콘솔 접속 시 실행 창에 표시된 **초기 설정 코드**를 입력하고 관리자 계정을 한 번 생성합니다.

> 학교 네트워크가 기기 간 통신을 막는 경우 휴대전화 핫스팟이나 동아리 공유기를 사용하거나, 아래의 Streamlit Community Cloud 배포를 사용하세요.

## 행사 당일 권장 배치

| 장치 | 화면 | 주소 모드 |
|---|---|---|
| 입구 노트북/태블릿 | 방문자 입력만 표시 | `?view=kiosk` |
| 메인 운영 컴퓨터 | 포인트·퇴장·명단 관리 | `?view=admin` |
| 빔프로젝터/TV | 익명 순위·현황 | `?view=board` |

한 컴퓨터에서 여러 탭을 띄워도 되고, 여러 기기가 동시에 접속해도 같은 데이터가 보입니다.

## GitHub + Streamlit Community Cloud 배포

1. 이 프로젝트를 GitHub 저장소에 올립니다.
2. Streamlit Community Cloud에서 저장소와 `app.py`를 선택합니다.
3. 영구 저장을 위해 PostgreSQL 데이터베이스를 준비합니다. 로컬 기본값인 SQLite는 클라우드 앱 재시작 시 데이터가 사라질 수 있어 실제 행사에는 권장하지 않습니다.
4. `.streamlit/secrets.example.toml` 형식대로 `DATABASE_URL`, `FIELD_ENCRYPTION_KEY`, `INITIAL_SETUP_CODE`, `APP_TIMEZONE`을 Streamlit의 **Settings → Secrets**에 저장합니다.
5. 배포 후 `?view=kiosk`, `?view=board`, `?view=admin` 주소를 각 장치에 북마크합니다.

`INITIAL_SETUP_CODE`를 변경한 뒤에는 열려 있던 관리자 페이지를 한 번 새로고침합니다. 앱은 새 설정을 다시 읽으며, 관리자 등록 화면에 **직접 지정한 초기 설정 코드가 연결되었습니다**라는 안내가 표시됩니다.

암호화 키는 아래 명령으로 만들 수 있습니다.

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

비밀값은 GitHub 파일에 넣지 않습니다. Streamlit 공식 문서도 `secrets.toml`을 저장소에 커밋하지 않고 클라우드 Secrets 화면에 입력하도록 안내합니다.

## 운영 체크리스트

### 행사 전날

- 운영자 계정 생성 및 로그인 확인
- 두 글자 ID와 빠른 포인트 입력 확인
- 휴대전화 2대로 동시 입장 테스트
- 포인트 증감과 퇴장 처리 테스트
- CSV 다운로드 확인
- 메인 컴퓨터 절전 모드 해제
- 같은 Wi-Fi에서 키오스크/현황판 주소 접속 확인

### 행사 종료 직후

- 방문 명단 CSV와 포인트 이력 CSV 다운로드
- 파일을 운영 책임자에게 전달하고 공개 공유 금지
- 설정한 보관기간 이후 개인정보 익명화 실행

## 데이터 구조와 안전장치

- 전화번호 원문은 Fernet 방식으로 암호화됩니다.
- 검색용으로 SHA-256 해시와 뒤 4자리만 별도 저장합니다.
- 순위표 공개에 동의하지 않으면 이름은 자동 마스킹되며, 운영용 두 글자 ID는 표시됩니다.
- 포인트는 음수가 될 수 없고, 변경마다 활동명·운영자·시각·변경 후 잔액이 기록됩니다.
- 퇴장 정산값이 시스템 잔액과 다르면 정산 변경 이력이 자동 생성됩니다.
- 관리자 비밀번호는 scrypt 해시로 저장됩니다.

## 개발 및 테스트

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/streamlit run app.py
```

## 기술 구성

- Python 3.11+
- Streamlit
- SQLAlchemy (SQLite/PostgreSQL 공용)
- Cryptography/Fernet
- Plotly

## 주의

이 앱은 학교 축제 운영용입니다. 실제 화폐, 유료 칩, 현금성 상품권의 구매·판매·환전·배팅 기능을 추가하지 마세요. 참가자 개인정보의 수집 문구와 보관기간은 학교 담당 교사의 확인을 받는 것이 좋습니다.
