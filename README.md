# PATCH Festival Lounge

학교 축제의 입장, 활동 포인트, 실시간 현황, 퇴장 정산을 한 번에 처리하는 Streamlit 운영 시스템입니다. 라운지 디자인을 사용하지만 실제 도박이나 배팅 기능은 없으며, 칩은 행사 내 간식 교환과 게임 점수 기록에만 사용하는 비현금성 단위입니다.

## 완성된 기능

- 방문자용 입장 키오스크: 이름, 나이, 전화번호, VIP/일반 구분
- 입장 화면과 다른 붉은 디자인의 독립 퇴장 화면: 두 글자 ID 확인 후 즉시 처리
- 전화번호 기준 중복 입장 방지와 기억하기 쉬운 영문 대문자 2글자 고유 ID 발급
- `300RT140` 입력으로 RT 참가자의 사용 칩 300P와 획득 점수 140P를 한 번에 기록
- `획득 점수 - 사용 칩` 차액을 현재 잔액에 자동 반영
- 전산 칩 관리 화면 진입 즉시 자동 선택되는 단일 입력창
- 사용 칩, 획득 점수, 차액 및 변경 후 잔액 이력 보존
- 이름, 입장 코드, 전화번호 뒤 4자리 검색
- 퇴장 시 실물 보유 포인트 확인 및 최종값 저장
- 실수로 처리한 퇴장 복구
- VIP와 일반 참가자를 분리한 두 개의 2초 자동 갱신 라이브 보드
- 각 보드의 TOP 3 시상대와 개인정보 보호형 전체 순위표
- 전화번호 암호화 저장과 공개 화면 개인정보 마스킹
- 관리자 아이디 없이 공용 비밀번호 한 칸만 사용하는 운영자 콘솔
- 운영자 콘솔과 다른 전용 비밀번호를 사용하는 방문·체류 영업 분석 화면
- 시간대별 방문자 수, 입퇴장 현황, VIP·일반 비율, 평균 체류시간, 개인별 입퇴장 정보
- 보관기간이 지난 개인정보의 되돌릴 수 없는 익명화
- SQLite 로컬 운영 및 PostgreSQL 클라우드 운영 지원

## 가장 쉬운 실행 방법 — 학교 현장 권장

행사장 메인 컴퓨터에서 `run_windows.bat`을 더블클릭합니다. 최초 한 번은 패키지 설치로 몇 분이 걸릴 수 있습니다. 실행 창에 다음과 같은 주소가 표시됩니다.

- 메인: `http://localhost:8501/`
- 입장 키오스크: `http://메인컴퓨터IP:8501/?view=kiosk`
- 퇴장 처리: `http://메인컴퓨터IP:8501/?view=checkout`
- VIP 실시간 현황판: `http://메인컴퓨터IP:8501/?view=board&category=vip`
- 일반 실시간 현황판: `http://메인컴퓨터IP:8501/?view=board&category=general`
- 운영자 콘솔: `http://메인컴퓨터IP:8501/?view=admin`
- 영업 분석: `http://메인컴퓨터IP:8501/?view=analytics`

입장용 컴퓨터와 현황판 컴퓨터를 메인 컴퓨터와 같은 Wi-Fi에 연결한 뒤 해당 주소를 열면 됩니다. 운영자 콘솔은 공용 비밀번호만 입력해 열며 관리자 아이디는 사용하지 않습니다.

> 학교 네트워크가 기기 간 통신을 막는 경우 휴대전화 핫스팟이나 동아리 공유기를 사용하거나, 아래의 Streamlit Community Cloud 배포를 사용하세요.

## 행사 당일 권장 배치

| 장치 | 화면 | 주소 모드 |
|---|---|---|
| 입구 노트북/태블릿 | 방문자 입력만 표시 | `?view=kiosk` |
| 퇴구 노트북/태블릿 | 두 글자 ID 퇴장 처리 | `?view=checkout` |
| 메인 운영 컴퓨터 | 전산 기록·영업 분석·명단 관리 | `?view=admin` |
| VIP 빔프로젝터/TV | VIP 순위·현황 | `?view=board&category=vip` |
| 일반 빔프로젝터/TV | 일반 순위·현황 | `?view=board&category=general` |

한 컴퓨터에서 여러 탭을 띄워도 되고, 여러 기기가 동시에 접속해도 같은 데이터가 보입니다.

## GitHub + Streamlit Community Cloud 배포

1. 이 프로젝트를 GitHub 저장소에 올립니다.
2. Streamlit Community Cloud에서 저장소와 `app.py`를 선택합니다.
3. 영구 저장을 위해 PostgreSQL 데이터베이스를 준비합니다. 로컬 기본값인 SQLite는 클라우드 앱 재시작 시 데이터가 사라질 수 있어 실제 행사에는 권장하지 않습니다.
4. `.streamlit/secrets.example.toml` 형식대로 `DATABASE_URL`, `FIELD_ENCRYPTION_KEY`, `OPERATOR_PASSWORD`, `ANALYTICS_PASSWORD`, `APP_TIMEZONE`을 Streamlit의 **Settings → Secrets**에 저장합니다.
5. 배포 후 `?view=kiosk`, `?view=checkout`, `?view=board&category=vip`, `?view=board&category=general`, `?view=admin`, `?view=analytics` 주소를 각 장치에 북마크합니다.

암호화 키는 아래 명령으로 만들 수 있습니다.

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

운영자 공용 비밀번호는 `OPERATOR_PASSWORD`, 영업 분석 비밀번호는 `ANALYTICS_PASSWORD` 값으로 지정하며 두 값은 서로 달라야 합니다. 비밀번호와 다른 비밀값은 GitHub 파일에 넣지 않습니다. Streamlit 공식 문서도 `secrets.toml`을 저장소에 커밋하지 않고 클라우드 Secrets 화면에 입력하도록 안내합니다.

## 운영 체크리스트

### 행사 전날

- 두 글자 ID와 `사용 칩 + ID + 획득 점수` 입력 확인
- VIP·일반 보드에 해당 참가자만 표시되는지 확인
- 운영자 공용 비밀번호 확인
- 영업 분석 비밀번호가 운영자 비밀번호와 다른지 확인
- 퇴장 화면에서 ID 확인과 최종 퇴장 처리 확인
- 휴대전화 2대로 동시 입장 테스트
- 포인트 증감과 퇴장 처리 테스트
- 메인 컴퓨터 절전 모드 해제
- 같은 Wi-Fi에서 키오스크/현황판 주소 접속 확인

### 행사 종료 직후

- 행사 운영 데이터 최종 확인
- 파일을 운영 책임자에게 전달하고 공개 공유 금지
- 설정한 보관기간 이후 개인정보 익명화 실행

## 데이터 구조와 안전장치

- 전화번호 원문은 Fernet 방식으로 암호화됩니다.
- 검색용으로 SHA-256 해시와 뒤 4자리만 별도 저장합니다.
- 개인정보 및 순위 공개 동의는 학교의 현장 안내·실물 동의 절차로 진행하며 앱에서는 별도 체크박스를 표시하지 않습니다.
- 포인트는 음수가 될 수 없고, 입력마다 사용 칩·획득 점수·차액·시각·변경 후 잔액이 기록됩니다.
- 퇴장 정산값이 시스템 잔액과 다르면 정산 변경 이력이 자동 생성됩니다.

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

이 앱은 학교 축제 운영용입니다. 실제 화폐, 유료 칩, 현금성 상품권의 구매·판매·환전·배팅 기능을 추가하지 마세요. 칩 사용은 행사 내 간식 교환처럼 결과와 무관한 용도로만 기록합니다. 참가자 개인정보의 수집 문구와 보관기간은 학교 담당 교사의 확인을 받는 것이 좋습니다.
