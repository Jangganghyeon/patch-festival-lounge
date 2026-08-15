from __future__ import annotations

import html
import time
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from .config import get_setting
from .service import LoungeService


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def top_brand(service: LoungeService, eyebrow: str) -> None:
    settings = service.settings()
    st.markdown(
        f"""
        <div class="brand-kicker">{esc(eyebrow)}</div>
        <div style="font-family:'Playfair Display',serif;font-size:1.55rem;font-weight:700;color:#f7f1df">
          {esc(settings.get("event_name", "PATCH FESTIVAL LOUNGE"))}
        </div>
        """,
        unsafe_allow_html=True,
    )


def footer() -> None:
    st.markdown(
        "<div class='footer-note'>학교 축제 운영 전용 · 포인트는 현금 가치가 없으며 구매·환전·배팅할 수 없습니다.</div>",
        unsafe_allow_html=True,
    )


def render_home(service: LoungeService) -> None:
    settings = service.settings()
    st.markdown(
        f"""
        <div class="brand-kicker">PATCH SOFTWARE CLUB · FESTIVAL SYSTEM</div>
        <h1 class="hero-title">{esc(settings.get("event_name"))}</h1>
        <div class="hero-subtitle">{esc(settings.get("event_subtitle"))}<br>
        입장부터 활동 포인트와 퇴장 정산까지, 한 화면에서 흐르는 축제 운영 시스템.</div>
        <div style="margin-top:1.2rem"><span class="safe-pill">● NON-CASH FESTIVAL POINTS</span></div>
        <div class="gold-rule"></div>
        """,
        unsafe_allow_html=True,
    )

    columns = st.columns(3)
    cards = [
        (
            "01",
            "입장 등록",
            "방문자가 직접 이름·나이·연락처·참가 유형을 입력합니다.",
            "입장 화면 열기",
            "?view=kiosk",
        ),
        (
            "02",
            "라이브 보드",
            "현재 입장 인원과 익명화된 포인트 순위를 실시간 표시합니다.",
            "현황판 열기",
            "?view=board",
        ),
        (
            "03",
            "운영자 콘솔",
            "포인트 기록, 퇴장 정산, 명단 및 데이터를 관리합니다.",
            "관리 화면 열기",
            "?view=admin",
        ),
    ]
    for col, (number, title, copy, label, href) in zip(columns, cards, strict=True):
        with col:
            st.markdown(
                f"<div class='mode-card'><div class='mode-num'>{number}</div><div class='mode-title'>{esc(title)}</div><div class='mode-copy'>{esc(copy)}</div></div>",
                unsafe_allow_html=True,
            )
            st.link_button(label, href, use_container_width=True)

    st.markdown("### 운영 상태")
    stats = service.dashboard()
    st.markdown(
        metric_cards(
            [
                ("오늘 누적 입장", stats["total"]),
                ("현재 라운지", stats["active"]),
                ("퇴장 완료", stats["exited"]),
                ("운영 중 포인트", f"{stats['active_points']:,}"),
            ]
        ),
        unsafe_allow_html=True,
    )
    footer()


def render_kiosk(service: LoungeService) -> None:
    top_brand(service, "GUEST CHECK-IN")
    st.markdown("## 게임 라운지 입장 등록")
    st.caption("입력 정보는 입·퇴장 및 축제 운영에만 사용됩니다.")

    if st.session_state.get("last_ticket"):
        ticket = st.session_state["last_ticket"]
        st.markdown(
            f"""
            <div class="ticket-card">
              <div class="ticket-label">ADMISSION COMPLETE · 입장 완료</div>
              <div style="margin:.8rem 0 1.3rem;color:#f7f1df;font-size:1.35rem;font-weight:800">환영합니다, {esc(ticket["name"])}님</div>
              <div class="ticket-code">{esc(ticket["code"])}</div>
              <div style="color:#a5b6ae;margin-top:.7rem">입장 코드 · 시작 포인트 {ticket["points"]:,} P</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.info(
            "입장 코드를 기억하거나 화면을 촬영해 주세요. 퇴장 시 이름이나 전화번호 뒤 4자리로도 검색할 수 있습니다."
        )
        if st.button("다음 방문자 등록", type="primary", use_container_width=True):
            del st.session_state["last_ticket"]
            st.rerun()
        st.link_button("처음 화면으로", "?view=home", use_container_width=True)
        footer()
        return

    with st.form("check_in_form", clear_on_submit=False):
        left, right = st.columns(2)
        with left:
            name = st.text_input("이름 *", max_chars=40, placeholder="홍길동")
            age = st.number_input("나이 *", min_value=7, max_value=100, value=17, step=1)
        with right:
            phone = st.text_input("전화번호 *", max_chars=15, placeholder="010-1234-5678")
            category_label = st.radio(
                "참가 유형 *",
                ["일반", "VIP"],
                horizontal=True,
                help="VIP 여부는 운영진 안내에 따라 선택하세요.",
            )
        st.markdown("##### 개인정보 및 공개 설정")
        consent = st.checkbox("입·퇴장 기록을 위해 이름, 나이, 전화번호를 수집·이용하는 데 동의합니다. *")
        leaderboard = st.checkbox("라이브 순위표에 내 이름을 공개하는 데 동의합니다. (선택)")
        submitted = st.form_submit_button("게임 라운지 참가", type="primary", use_container_width=True)
    if submitted:
        try:
            result = service.check_in(
                name=name,
                age=int(age),
                phone=phone,
                category="vip" if category_label == "VIP" else "general",
                privacy_consent=consent,
                leaderboard_opt_in=leaderboard,
            )
            st.session_state["last_ticket"] = {
                "name": name.strip(),
                "code": result.display_code,
                "points": result.starting_points,
            }
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    st.link_button("처음 화면으로", "?view=home")
    footer()


def metric_cards(items: list[tuple[str, object]]) -> str:
    blocks = "".join(
        f"<div class='metric-card'><div class='metric-label'>{esc(label)}</div><div class='metric-value'>{esc(value)}</div></div>"
        for label, value in items
    )
    return f"<div class='metric-grid'>{blocks}</div>"


def leaderboard_html(rows: list[dict]) -> str:
    if not rows:
        return "<div class='panel-card' style='color:#a5b6ae'>아직 순위 데이터가 없습니다.</div>"
    body = []
    for index, row in enumerate(rows, 1):
        badge = "VIP" if row["category"] == "vip" else "GENERAL"
        body.append(
            f"""
            <div class="rank-row">
              <div class="rank-number">{index:02d}</div>
              <div><div class="rank-name">{esc(row["name"])}</div><div class="rank-code">{esc(row["code"])} · {badge}</div></div>
              <div class="rank-points">{row["points"]:,} P</div>
            </div>
            """
        )
    return "<div class='panel-card'>" + "".join(body) + "</div>"


def render_board(service: LoungeService) -> None:
    top_brand(service, "LIVE OPERATIONS BOARD")
    st.markdown(
        "<div style='color:#a5b6ae'><span class='live-dot'></span>5초마다 자동 갱신</div>",
        unsafe_allow_html=True,
    )

    @st.fragment(run_every="5s")
    def live_board() -> None:
        stats = service.dashboard()
        st.markdown(
            metric_cards(
                [
                    ("현재 입장", stats["active"]),
                    ("누적 방문", stats["total"]),
                    ("VIP 입장", stats["vip_active"]),
                    ("현재 총 포인트", f"{stats['active_points']:,}"),
                ]
            ),
            unsafe_allow_html=True,
        )
        left, right = st.columns([1.15, 0.85], gap="large")
        with left:
            st.markdown("### 현재 포인트 순위")
            st.markdown(leaderboard_html(stats["leaderboard"]), unsafe_allow_html=True)
        with right:
            st.markdown("### 입장 흐름")
            traffic = pd.DataFrame(stats["traffic"])
            if traffic.empty:
                st.info("입장 데이터가 쌓이면 시간대별 흐름이 표시됩니다.")
            else:
                fig = px.bar(traffic, x="시간", y="입장", text_auto=True)
                fig.update_traces(marker_color="#dcbf73", hovertemplate="%{x}<br>%{y}명<extra></extra>")
                fig.update_layout(
                    height=310,
                    margin=dict(l=0, r=0, t=8, b=0),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#d9e2de",
                    xaxis=dict(showgrid=False),
                    yaxis=dict(gridcolor="rgba(220,191,115,.12)", title=None),
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown("### 최근 입장")
            for row in stats["recent"][:5]:
                st.markdown(
                    f"<div class='rank-row' style='grid-template-columns:minmax(0,1fr) 70px'><div><div class='rank-name'>{esc(row['name'])}</div><div class='rank-code'>{esc(row['code'])} · {service.format_time(row['checked_in_at'])}</div></div><div class='rank-points' style='font-size:.8rem'>{'입장 중' if row['status'] == 'active' else '퇴장'}</div></div>",
                    unsafe_allow_html=True,
                )

    live_board()
    st.link_button("처음 화면으로", "?view=home")
    footer()


def _initial_admin_setup(service: LoungeService) -> None:
    top_brand(service, "FIRST-RUN SECURITY SETUP")
    st.markdown("## 최초 관리자 등록")
    if get_setting("INITIAL_SETUP_CODE"):
        st.success("Streamlit에서 직접 지정한 초기 설정 코드가 연결되었습니다.")
    else:
        st.warning(
            "고정 초기 설정 코드가 아직 연결되지 않았습니다. 로컬 실행 시에는 실행 창에 표시된 임시 코드를 사용합니다."
        )
    st.caption("코드를 방금 변경했다면 이 페이지를 한 번 새로고침한 뒤 입력하세요.")
    with st.form("first_admin"):
        setup_code = st.text_input(
            "초기 설정 코드",
            type="password",
            help="Streamlit 앱 설정의 Secrets에 저장한 INITIAL_SETUP_CODE 값입니다.",
        )
        username = st.text_input("관리자 아이디", placeholder="patch_admin")
        password = st.text_input("비밀번호", type="password", help="8자 이상")
        confirmation = st.text_input("비밀번호 확인", type="password")
        submitted = st.form_submit_button("관리자 계정 생성", type="primary", use_container_width=True)
    if submitted:
        if password != confirmation:
            st.error("비밀번호 확인이 일치하지 않습니다.")
        else:
            try:
                service.create_first_admin(username, password, setup_code)
                st.success("관리자 계정이 생성되었습니다. 로그인 화면으로 이동합니다.")
                time.sleep(0.7)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


def _admin_login(service: LoungeService) -> None:
    top_brand(service, "AUTHORIZED STAFF ONLY")
    st.markdown("## 운영자 로그인")
    locked_until = st.session_state.get("login_locked_until", 0.0)
    if time.time() < locked_until:
        st.error("로그인 시도가 잠시 제한되었습니다. 30초 후 다시 시도해 주세요.")
        return
    with st.form("admin_login"):
        username = st.text_input("아이디")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인", type="primary", use_container_width=True)
    if submitted:
        ok, role = service.authenticate(username, password)
        if ok:
            st.session_state["auth"] = {"username": username.strip(), "role": role}
            st.session_state["login_failures"] = 0
            st.rerun()
        else:
            failures = int(st.session_state.get("login_failures", 0)) + 1
            st.session_state["login_failures"] = failures
            if failures >= 5:
                st.session_state["login_locked_until"] = time.time() + 30
            st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
    st.link_button("처음 화면으로", "?view=home")


def participant_strip(item: dict) -> None:
    label = "VIP" if item["category"] == "vip" else "일반"
    st.markdown(
        f"""
        <div class="person-strip">
          <div style="display:flex;justify-content:space-between;gap:1rem;align-items:center">
            <div><div class="person-name">{esc(item["name"])}</div><div class="person-meta">{esc(item["code"])} · {label} · {esc(item["phone"])}</div></div>
            <div class="balance">{item["points"]:,} P</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def participant_picker(service: LoungeService, key: str, active_only: bool = True) -> dict | None:
    query = st.text_input("이름 · 입장 코드 · 전화번호 뒤 4자리 검색", key=f"{key}_query")
    if not query.strip():
        st.caption("검색어를 입력하면 일치하는 참가자가 표시됩니다.")
        return None
    results = service.search_participants(query, active_only=active_only, limit=20)
    if not results:
        st.warning("검색 결과가 없습니다.")
        return None
    labels = {
        row["id"]: f"{row['name']} · {row['code']} · {row['phone']} · {row['points']:,}P" for row in results
    }
    selected_id = st.selectbox(
        "참가자 선택", options=list(labels), format_func=lambda value: labels[value], key=f"{key}_selected"
    )
    selected = next(row for row in results if row["id"] == selected_id)
    participant_strip(selected)
    return selected


def render_admin(service: LoungeService) -> None:
    if not service.has_admin():
        _initial_admin_setup(service)
        footer()
        return
    if "auth" not in st.session_state:
        _admin_login(service)
        footer()
        return

    auth = st.session_state["auth"]
    top_brand(service, "OPERATIONS CONSOLE")
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.markdown(
            f"## 운영자 콘솔 <span style='color:#a5b6ae;font-size:.9rem'>· {esc(auth['username'])}</span>",
            unsafe_allow_html=True,
        )
    with top_right:
        if st.button("로그아웃", use_container_width=True):
            del st.session_state["auth"]
            st.rerun()

    tabs = st.tabs(["실시간 현황", "포인트 기록", "퇴장 처리", "방문 명단", "설정 · 백업"])
    with tabs[0]:
        _admin_overview(service)
    with tabs[1]:
        _points_console(service, auth["username"])
    with tabs[2]:
        _checkout_console(service, auth["username"])
    with tabs[3]:
        _participant_list(service, auth["username"])
    with tabs[4]:
        _settings_console(service, auth["username"])
    footer()


def _admin_overview(service: LoungeService) -> None:
    @st.fragment(run_every="5s")
    def live_admin() -> None:
        stats = service.dashboard()
        st.markdown(
            metric_cards(
                [
                    ("현재 입장", stats["active"]),
                    ("누적 방문", stats["total"]),
                    ("퇴장 완료", stats["exited"]),
                    ("VIP 입장", stats["vip_active"]),
                ]
            ),
            unsafe_allow_html=True,
        )
        left, right = st.columns([1.05, 0.95], gap="large")
        with left:
            st.markdown("#### 실시간 순위")
            st.markdown(leaderboard_html(stats["leaderboard"][:7]), unsafe_allow_html=True)
        with right:
            st.markdown("#### 최근 포인트 기록")
            txs = service.recent_transactions(8)
            if not txs:
                st.info("아직 포인트 기록이 없습니다.")
            else:
                table = pd.DataFrame(
                    [
                        {
                            "시각": service.format_time(tx["time"]),
                            "참가자": f"{tx['name']} ({tx['code']})",
                            "변동": f"{tx['delta']:+,}",
                            "잔액": f"{tx['balance']:,}",
                            "활동": tx["activity"],
                        }
                        for tx in txs
                    ]
                )
                st.dataframe(table, hide_index=True, use_container_width=True)
        st.caption("● 5초 자동 갱신")

    live_admin()


def _points_console(service: LoungeService, operator: str) -> None:
    st.markdown("### 활동 포인트 기록")
    st.caption("게임 결과를 자동 산출하지 않습니다. 운영자가 확인한 축제 포인트만 기록합니다.")
    selected = participant_picker(service, "points", active_only=True)
    if not selected:
        return
    with st.form("points_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            delta = st.number_input("포인트 변동", min_value=-100000, max_value=100000, value=10, step=5)
        with col2:
            activity = st.selectbox(
                "게임/활동", ["테이블 A", "테이블 B", "미니게임", "이벤트 보너스", "운영 정정"]
            )
        note = st.text_input("메모 (선택)", max_chars=200, placeholder="라운드·운영 사유 등")
        submitted = st.form_submit_button("포인트 기록", type="primary", use_container_width=True)
    if submitted:
        try:
            balance = service.adjust_points(selected["id"], int(delta), activity, note, operator)
            st.success(f"{selected['name']}님의 포인트가 {int(delta):+,}P 반영되었습니다. 현재 {balance:,}P")
        except ValueError as exc:
            st.error(str(exc))


def _checkout_console(service: LoungeService, operator: str) -> None:
    st.markdown("### 퇴장 및 최종 정산")
    selected = participant_picker(service, "checkout", active_only=True)
    if not selected:
        return
    with st.form("checkout_form"):
        final_points = st.number_input(
            "실물 보유 포인트/칩 수", min_value=0, max_value=1_000_000, value=int(selected["points"]), step=1
        )
        note = st.text_input("교환·퇴장 메모 (선택)", max_chars=200, placeholder="예: 상품 교환 완료")
        confirmed = st.checkbox("본인과 최종 수량을 확인했습니다.")
        submitted = st.form_submit_button("퇴장 완료", type="primary", use_container_width=True)
    if submitted:
        if not confirmed:
            st.error("확인 항목을 체크해 주세요.")
        else:
            try:
                service.check_out(selected["id"], int(final_points), note, operator)
                st.success(f"{selected['name']}님의 퇴장이 기록되었습니다. 최종 {int(final_points):,}P")
            except ValueError as exc:
                st.error(str(exc))


def _participant_list(service: LoungeService, operator: str) -> None:
    st.markdown("### 방문 명단")
    search = st.text_input("명단 검색", key="list_search", placeholder="이름·코드·전화번호 뒤 4자리")
    status = st.radio("상태", ["전체", "입장 중", "퇴장"], horizontal=True)
    reveal = st.checkbox("전화번호 전체 보기 (관리자 화면에서만)")
    rows = service.search_participants(search, active_only=status == "입장 중", limit=500)
    if status == "퇴장":
        rows = [row for row in rows if row["status"] == "exited"]
    if reveal:
        rows = [service.get_participant(row["id"], reveal_phone=True) for row in rows]
    table = pd.DataFrame(
        [
            {
                "코드": row["code"],
                "이름": row["name"],
                "나이": row["age"],
                "전화번호": row["phone"],
                "구분": "VIP" if row["category"] == "vip" else "일반",
                "상태": "입장 중" if row["status"] == "active" else "퇴장",
                "포인트": row["points"],
                "입장": service.format_time(row["checked_in_at"], include_date=True),
                "퇴장": service.format_time(row["checked_out_at"], include_date=True),
            }
            for row in rows
        ]
    )
    st.dataframe(table, hide_index=True, use_container_width=True, height=420)
    st.caption(f"검색 결과 {len(rows)}명")

    exited = [row for row in rows if row["status"] == "exited"]
    if exited:
        with st.expander("잘못 처리한 퇴장 복구"):
            labels = {
                row[
                    "id"
                ]: f"{row['name']} · {row['code']} · {service.format_time(row['checked_out_at'], True)}"
                for row in exited
            }
            chosen = st.selectbox("복구할 참가자", list(labels), format_func=lambda value: labels[value])
            if st.button("입장 중 상태로 복구"):
                try:
                    service.reopen_participant(chosen, operator)
                    st.success("퇴장 기록이 복구되었습니다.")
                except ValueError as exc:
                    st.error(str(exc))


def _settings_console(service: LoungeService, operator: str) -> None:
    settings = service.settings()
    st.markdown("### 행사 설정")
    with st.form("settings_form"):
        event_name = st.text_input("행사명", value=settings.get("event_name", ""), max_chars=80)
        subtitle = st.text_input("부제", value=settings.get("event_subtitle", ""), max_chars=120)
        a, b, c = st.columns(3)
        with a:
            general_start = st.number_input(
                "일반 시작 포인트",
                min_value=0,
                max_value=100000,
                value=int(settings.get("general_start_points", "0")),
            )
        with b:
            vip_start = st.number_input(
                "VIP 시작 포인트",
                min_value=0,
                max_value=100000,
                value=int(settings.get("vip_start_points", "20")),
            )
        with c:
            board_size = st.number_input(
                "순위표 인원", min_value=3, max_value=30, value=int(settings.get("leaderboard_size", "10"))
            )
        retention = st.number_input(
            "퇴장 후 개인정보 보관일",
            min_value=1,
            max_value=365,
            value=int(settings.get("privacy_retention_days", "30")),
        )
        submitted = st.form_submit_button("설정 저장", type="primary")
    if submitted:
        try:
            service.update_settings(
                {
                    "event_name": event_name,
                    "event_subtitle": subtitle,
                    "general_start_points": str(general_start),
                    "vip_start_points": str(vip_start),
                    "leaderboard_size": str(board_size),
                    "privacy_retention_days": str(retention),
                },
                operator,
            )
            st.success("설정을 저장했습니다.")
        except ValueError as exc:
            st.error(str(exc))

    st.markdown("### 데이터 백업")
    st.caption("전화번호가 포함된 파일이므로 다운로드 후 운영 책임자만 보관하세요.")
    c1, c2 = st.columns(2)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    with c1:
        st.download_button(
            "방문 명단 CSV 다운로드",
            data=service.export_participants_csv(),
            file_name=f"festival_participants_{stamp}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with c2:
        st.download_button(
            "포인트 이력 CSV 다운로드",
            data=service.export_transactions_csv(),
            file_name=f"festival_points_{stamp}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with st.expander("보관기간이 지난 개인정보 익명화"):
        st.write(f"현재 보관기간: 퇴장 후 {settings.get('privacy_retention_days', '30')}일")
        confirm = st.checkbox("대상자의 이름·전화번호를 되돌릴 수 없게 익명화합니다.", key="purge_confirm")
        if st.button("기한 만료 개인정보 익명화", disabled=not confirm):
            count = service.purge_expired_personal_data(operator)
            st.success(f"{count}명의 개인정보를 익명화했습니다.")

    with st.expander("내 비밀번호 변경"):
        with st.form("password_change"):
            current = st.text_input("현재 비밀번호", type="password")
            new = st.text_input("새 비밀번호", type="password")
            new_confirm = st.text_input("새 비밀번호 확인", type="password")
            change = st.form_submit_button("비밀번호 변경")
        if change:
            if new != new_confirm:
                st.error("새 비밀번호 확인이 일치하지 않습니다.")
            else:
                try:
                    service.change_password(operator, current, new)
                    st.success("비밀번호를 변경했습니다.")
                except ValueError as exc:
                    st.error(str(exc))
