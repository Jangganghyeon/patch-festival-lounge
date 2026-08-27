from __future__ import annotations

import html
import math
import time
from datetime import timedelta

import streamlit as st

from .quick_input import quick_point_input
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
        "<div class='footer-note'>학교 축제 운영 전용 · 칩은 현금 가치가 없으며 행사 내 간식 교환과 게임 점수 기록에만 사용됩니다.</div>",
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

    primary_columns = st.columns(2, gap="large")
    primary_cards = [
        (
            "01",
            "입장 등록",
            "방문자가 직접 이름·나이·연락처를 입력합니다.",
            "입장 화면 열기",
            "?view=kiosk",
        ),
        (
            "02",
            "퇴장 처리",
            "이름·전화번호·고유 ID를 확인하고 퇴장을 완료합니다.",
            "퇴장 화면 열기",
            "?view=checkout",
        ),
    ]
    for col, (number, title, copy, label, href) in zip(
        primary_columns, primary_cards, strict=True
    ):
        with col:
            st.markdown(
                f"<div class='mode-card'><div class='mode-num'>{number}</div>"
                f"<div class='mode-title'>{esc(title)}</div><div class='mode-copy'>{esc(copy)}</div></div>",
                unsafe_allow_html=True,
            )
            st.link_button(label, href, use_container_width=True)

    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)
    secondary_columns = st.columns(2, gap="large")
    secondary_cards = [
        (
            "03",
            "일반 라이브 보드",
            "일반 참가자의 TOP 3와 포인트 순위를 실시간 표시합니다.",
            "일반 보드 열기",
            "?view=board&category=general",
        ),
        (
            "04",
            "운영자 콘솔",
            "전산 기록, 영업 분석, 방문 명단을 관리합니다.",
            "관리 화면 열기",
            "?view=admin",
        ),
    ]
    for col, (number, title, copy, label, href) in zip(
        secondary_columns, secondary_cards, strict=True
    ):
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
                ("누적 입장", stats["total"]),
                ("현재 라운지", stats["active"]),
                ("퇴장 완료", stats["exited"]),
                ("운영 중 포인트", f"{stats['active_points']:,}"),
            ]
        ),
        unsafe_allow_html=True,
    )
    footer()


def render_checkout(service: LoungeService) -> None:
    top_brand(service, "GUEST CHECK-OUT")
    st.markdown(
        """
        <div class="checkout-hero">
          <div class="checkout-kicker">EXIT ONLY · 퇴장 전용 화면</div>
          <div class="checkout-title">퇴장 처리</div>
          <div class="checkout-copy">입장 등록 화면이 아닙니다. 입장할 때 작성한 이름·전화번호와 발급받은 ID를 입력해 주세요.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.get("checkout_complete"):
        completed = st.session_state["checkout_complete"]
        st.success(f"{completed['code']} · {completed['name']}님의 퇴장이 완료되었습니다.")
        if st.button("다음 참가자 퇴장", type="primary", use_container_width=True):
            st.session_state.pop("checkout_complete", None)
            st.session_state.pop("checkout_candidate_code", None)
            st.rerun()
        footer()
        return

    with st.container(key="checkout_station"):
        with st.form("checkout_identity_form"):
            name = st.text_input(
                "이름",
                max_chars=40,
                placeholder="홍길동",
                key="checkout_name_input",
            )
            phone = st.text_input(
                "전화번호",
                max_chars=15,
                placeholder="010-1234-5678",
                key="checkout_phone_input",
            )
            code = st.text_input(
                "참가자 ID",
                max_chars=4,
                placeholder="RT",
                key="checkout_code_input",
                help="입장할 때 발급받은 영문 2~4글자 고유 ID를 입력하세요.",
            )
            identity_submitted = st.form_submit_button(
                "입장 정보 확인", use_container_width=True
            )
        if identity_submitted:
            try:
                candidate = service.verify_checkout_identity(name=name, phone=phone, code=code)
                st.session_state["checkout_candidate_code"] = candidate["code"]
            except ValueError as exc:
                st.session_state.pop("checkout_candidate_code", None)
                st.error(str(exc))

        candidate_code = st.session_state.get("checkout_candidate_code")
        if candidate_code:
            try:
                candidate = service.active_participant_by_code(candidate_code)
                label = "VIP" if candidate["category"] == "vip" else "일반"
                st.markdown(
                    f"""
                    <div class="checkout-confirm-card">
                      <div class="checkout-confirm-label">퇴장 참가자 확인</div>
                      <div class="checkout-confirm-name">{esc(candidate['name'])}</div>
                      <div class="checkout-confirm-meta">ID {esc(candidate['code'])} · {label}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(
                    "위 참가자를 퇴장 처리",
                    type="primary",
                    use_container_width=True,
                    key="checkout_confirm_button",
                ):
                    service.check_out(
                        candidate["id"],
                        int(candidate["points"]),
                        "독립 퇴장 화면",
                        "checkout_station",
                    )
                    st.session_state["checkout_complete"] = {
                        "code": candidate["code"],
                        "name": candidate["name"],
                    }
                    st.session_state.pop("checkout_candidate_code", None)
                    st.rerun()
            except ValueError as exc:
                st.session_state.pop("checkout_candidate_code", None)
                st.error(str(exc))

    footer()


def render_kiosk(service: LoungeService) -> None:
    top_brand(service, "GUEST CHECK-IN")
    st.markdown("## 게임 라운지 입장 등록")
    st.caption("입력 정보는 입·퇴장 및 축제 운영에만 사용됩니다.")

    if st.session_state.get("last_ticket"):
        ticket = st.session_state["last_ticket"]
        point_label = "현재 포인트" if ticket["is_returning"] else "시작 포인트"
        if "last_ticket_expires_at" not in st.session_state:
            st.session_state["last_ticket_expires_at"] = time.monotonic() + 10
        st.markdown(
            f"""
            <div class="ticket-card">
              <div class="ticket-label">ADMISSION COMPLETE · 입장 완료</div>
              <div style="margin:.8rem 0 1.3rem;color:#f7f1df;font-size:1.35rem;font-weight:800">환영합니다, {esc(ticket["name"])}님</div>
              <div class="ticket-memory-label">반드시 기억하세요</div>
              <div class="ticket-code">{esc(ticket["code"])}</div>
              <div class="ticket-memory-title">이 문자가 나의 고유 참가자 ID입니다</div>
              <div class="ticket-memory-copy">활동 포인트를 받을 때마다 운영진에게 이 ID를 말해 주세요.</div>
              <div style="color:#a5b6ae;margin-top:.75rem">입장 횟수 {ticket["entry_count"]} / 5 · {point_label} {ticket["points"]:,} P</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.warning(f"중요: 나의 ID는 {ticket['code']}입니다. 화면을 닫기 전에 반드시 기억해 주세요.")

        @st.fragment(run_every=timedelta(seconds=1))
        def ticket_auto_advance() -> None:
            expires_at = float(st.session_state.get("last_ticket_expires_at", 0))
            remaining = max(0, math.ceil(expires_at - time.monotonic()))
            if remaining == 0:
                st.session_state.pop("last_ticket", None)
                st.session_state.pop("last_ticket_expires_at", None)
                st.rerun()
            st.caption(f"{remaining}초 후 다음 방문자 등록 화면으로 자동 전환됩니다.")

        ticket_auto_advance()
        if st.button("다음 방문자 등록", type="primary", use_container_width=True):
            st.session_state.pop("last_ticket", None)
            st.session_state.pop("last_ticket_expires_at", None)
            st.rerun()
        footer()
        return

    with st.container(key="check_in_kiosk"):
        with st.form("check_in_form", clear_on_submit=False):
            left, right = st.columns(2, gap="large")
            with left:
                with st.container(key="kiosk_guest_card"):
                    st.markdown(
                        "<div class='kiosk-section-kicker'>01 · GUEST PROFILE</div>"
                        "<div class='kiosk-section-title'>참가자 정보</div>"
                        "<div class='kiosk-section-copy'>이름과 나이를 정확하게 입력해 주세요.</div>",
                        unsafe_allow_html=True,
                    )
                    name = st.text_input("이름 *", max_chars=40, placeholder="홍길동")
                    age = st.number_input("나이 *", min_value=7, max_value=100, value=17, step=1)
            with right:
                with st.container(key="kiosk_access_card"):
                    st.markdown(
                        "<div class='kiosk-section-kicker'>02 · FESTIVAL ACCESS</div>"
                        "<div class='kiosk-section-title'>입장 정보</div>"
                        "<div class='kiosk-section-copy'>연락처를 정확하게 입력해 주세요.</div>",
                        unsafe_allow_html=True,
                    )
                    phone = st.text_input("전화번호 *", max_chars=15, placeholder="010-1234-5678")
            submitted = st.form_submit_button(
                "게임 라운지 참가",
                type="primary",
                use_container_width=True,
            )
    if submitted:
        try:
            result = service.check_in(
                name=name,
                age=int(age),
                phone=phone,
                category="general",
                privacy_consent=True,
                leaderboard_opt_in=True,
            )
            st.session_state["last_ticket"] = {
                "name": name.strip(),
                "code": result.display_code,
                "points": result.starting_points,
                "entry_count": result.entry_count,
                "is_returning": result.is_returning,
            }
            st.session_state["last_ticket_expires_at"] = time.monotonic() + 10
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    footer()


def metric_cards(items: list[tuple[str, object]]) -> str:
    blocks = "".join(
        f"<div class='metric-card'><div class='metric-label'>{esc(label)}</div><div class='metric-value'>{esc(value)}</div></div>"
        for label, value in items
    )
    return f"<div class='metric-grid'>{blocks}</div>"


def leaderboard_html(rows: list[dict], start_rank: int = 1) -> str:
    if not rows:
        return "<div class='panel-card' style='color:#a5b6ae'>4위 이하 참가자가 없습니다.</div>"
    body = []
    for index, row in enumerate(rows, start_rank):
        body.append(
            f'<div class="rank-row"><div class="rank-number">{index:02d}</div>'
            f'<div><div class="rank-name">{esc(row["name"])}</div>'
            f'<div class="rank-code">ID&nbsp; {esc(row["code"])}</div></div>'
            f'<div class="rank-points">{row["points"]:,} P</div></div>'
        )
    return "<div class='panel-card'>" + "".join(body) + "</div>"


def podium_html(rows: list[dict], group_label: str) -> str:
    ranked = {place: rows[place - 1] if len(rows) >= place else None for place in (1, 2, 3)}

    def podium_place(place: int) -> str:
        row = ranked[place]
        if row:
            name = esc(row["name"])
            code = esc(row["code"])
            points = f'{row["points"]:,} P'
        else:
            name, code, points = "도전자 대기", "--", "0 P"
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}[place]
        winner_mark = (
            '<div class="winner-crown">♛</div><div class="winner-ribbon">CHAMPION</div>'
            if place == 1
            else ""
        )
        return (
            f'<div class="podium-place podium-{place}">'
            f"{winner_mark}"
            f'<div class="podium-medal">{medal}</div>'
            f'<div class="podium-name">{name}</div>'
            f'<div class="podium-id">ID&nbsp; {code}</div>'
            f'<div class="podium-points">{points}</div>'
            f'<div class="podium-step"><span>{place}</span></div></div>'
        )

    return (
        '<div class="podium-shell"><div class="podium-stage-glow"></div>'
        '<div class="podium-sparkle sparkle-1">✦</div>'
        '<div class="podium-sparkle sparkle-2">✧</div>'
        '<div class="podium-sparkle sparkle-3">✦</div>'
        '<div class="podium-sparkle sparkle-4">✧</div>'
        f'<div class="podium-title"><span>TOP 3</span> · {esc(group_label)} LIVE RANKING</div>'
        '<div class="podium-grid">'
        + podium_place(2)
        + podium_place(1)
        + podium_place(3)
        + "</div></div>"
    )


def render_board(service: LoungeService) -> None:
    category = str(st.query_params.get("category", "general")).lower()
    if category not in {"vip", "general"}:
        category = "general"
    group_label = "VIP" if category == "vip" else "GENERAL"
    group_label_ko = "VIP" if category == "vip" else "일반 손님"

    top_brand(service, f"{group_label} LIVE OPERATIONS BOARD")
    st.markdown(f"## {group_label_ko} 라이브 보드")
    st.markdown(
        "<div style='color:#a5b6ae'><span class='live-dot'></span>2초마다 자동 갱신</div>",
        unsafe_allow_html=True,
    )

    @st.fragment(run_every=timedelta(seconds=2))
    def live_board() -> None:
        leaderboard = service.leaderboard(category)
        podium_column, ranking_column = st.columns([1.35, 0.65], gap="large", vertical_alignment="top")
        with podium_column:
            with st.container(key="board_podium"):
                st.markdown(
                    podium_html(leaderboard[:3], group_label),
                    unsafe_allow_html=True,
                )
        with ranking_column:
            with st.container(key="board_ranking"):
                st.markdown(
                    f"<div class='ranking-heading'><span>{esc(group_label)} PLAYERS</span>"
                    "<strong>4위부터 순위</strong></div>"
                    + leaderboard_html(leaderboard[3:], start_rank=4),
                    unsafe_allow_html=True,
                )

    live_board()
    st.link_button("처음 화면으로", "?view=home")
    footer()


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


def _open_admin_panel(panel: str) -> None:
    st.query_params["view"] = "admin"
    if panel == "menu":
        if "panel" in st.query_params:
            del st.query_params["panel"]
    else:
        st.query_params["panel"] = panel
    st.rerun()


def _admin_back_button(key: str) -> None:
    if st.button("← 운영자 메뉴로 돌아가기", key=key):
        _open_admin_panel("menu")


def _public_display_reset_panel(service: LoungeService, operator: str) -> None:
    st.markdown("## 라운지·라이브 보드 초기화")
    if not _reset_password_gate(service):
        return
    st.markdown(
        """
        <div class="panel-card">
          <strong>기록을 삭제하지 않는 표시 초기화</strong>
          <div class="mode-copy" style="margin-top:.55rem">
            방문 명단·입퇴장 기록·운영 기록은 그대로 보존됩니다.<br>
            초기화 이전 방문자만 라운지 현황과 두 라이브 보드에서 숨겨집니다.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    last_reset = service.public_display_reset_at()
    if last_reset:
        st.caption(f"최근 초기화: {service.format_time(last_reset, include_date=True)}")
    else:
        st.caption("아직 표시 초기화를 실행하지 않았습니다.")

    with st.form("public_display_reset_form"):
        confirmed = st.checkbox("운영자 기록은 유지되고 공개 화면 표시만 초기화됨을 확인했습니다.")
        submitted = st.form_submit_button(
            "라운지·라이브 보드 표시 초기화",
            type="primary",
            use_container_width=True,
        )
    if submitted:
        if not confirmed:
            st.warning("초기화 범위를 확인한 뒤 체크해 주세요.")
        else:
            service.reset_public_display(operator)
            st.success("표시를 초기화했습니다. 운영자 콘솔의 기존 기록은 그대로 유지됩니다.")


def render_admin(service: LoungeService) -> None:
    top_brand(service, "OPERATIONS CONSOLE")
    if not _operator_password_gate(service):
        footer()
        return

    operator = "festival_staff"
    panel = str(st.query_params.get("panel", "menu")).lower()

    if panel == "chips":
        _admin_back_button("admin_back_from_chips")
        st.markdown("## 전산 칩 관리")
        _quick_points_console(service, operator)
    elif panel == "analytics":
        _admin_back_button("admin_back_from_analytics")
        _render_analytics_panel(service)
    elif panel == "visitors":
        _admin_back_button("admin_back_from_visitors")
        _participant_list(service, operator)
    elif panel == "reset":
        _admin_back_button("admin_back_from_reset")
        _public_display_reset_panel(service, operator)
    else:
        st.markdown("## 운영자 콘솔")
        menu_items = [
            (
                "01",
                "전산 칩 관리",
                "참가자 ID와 포인트를 입력해 가장 빠르게 기록합니다.",
                "전산 칩 관리 열기",
                "chips",
            ),
            (
                "02",
                "영업 분석",
                "오늘의 방문·체류·입퇴장 흐름을 한눈에 확인합니다.",
                "영업 분석 열기",
                "analytics",
            ),
            (
                "03",
                "방문 명단",
                "현재 입장·퇴장 상태와 포인트를 확인합니다.",
                "방문 명단 열기",
                "visitors",
            ),
            (
                "04",
                "화면 표시 초기화",
                "기록은 보존하고 라운지와 라이브 보드 표시만 새로 시작합니다.",
                "초기화 기능 열기",
                "reset",
            ),
        ]
        for start in range(0, len(menu_items), 2):
            columns = st.columns(2, gap="large")
            for column, (number, title, copy, label, target) in zip(
                columns, menu_items[start : start + 2], strict=True
            ):
                with column:
                    st.markdown(
                        f'<div class="mode-card"><div class="mode-num">{number}</div>'
                        f'<div class="mode-title">{esc(title)}</div>'
                        f'<div class="mode-copy">{esc(copy)}</div></div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        label,
                        key=f"admin_open_{target}",
                        use_container_width=True,
                    ):
                        _open_admin_panel(target)
            if start == 0:
                st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)
    footer()


def _operator_password_gate(service: LoungeService) -> bool:
    if st.session_state.get("operator_authenticated") is True:
        return True

    st.markdown("## 운영자 콘솔")
    with st.container(key="operator_gate"):
        st.markdown(
            '<div class="operator-gate-copy">운영진 공용 비밀번호를 입력하면 바로 콘솔이 열립니다.</div>',
            unsafe_allow_html=True,
        )
        with st.form("operator_password_form", clear_on_submit=True):
            password = st.text_input(
                "운영자 비밀번호",
                type="password",
                placeholder="비밀번호 입력",
                autocomplete="current-password",
            )
            submitted = st.form_submit_button(
                "운영자 콘솔 열기", type="primary", use_container_width=True
            )
        if submitted:
            if service.verify_operator_password(password):
                st.session_state["operator_authenticated"] = True
                st.rerun()
            st.error("비밀번호가 올바르지 않습니다.")
    return False


def _analytics_password_gate(service: LoungeService) -> bool:
    if st.session_state.get("analytics_authenticated") is True:
        return True

    st.markdown("## 영업 분석")
    issue = service.analytics_password_issue()
    if issue:
        st.error(issue)
        st.caption("Streamlit Secrets에 운영자 비밀번호와 다른 ANALYTICS_PASSWORD를 설정해 주세요.")
        return False

    with st.container(key="analytics_gate"):
        st.markdown(
            '<div class="analytics-gate-copy">영업 분석 전용 비밀번호를 입력해 주세요.</div>',
            unsafe_allow_html=True,
        )
        with st.form("analytics_password_form", clear_on_submit=True):
            password = st.text_input(
                "영업 분석 비밀번호",
                type="password",
                placeholder="분석용 비밀번호 입력",
                autocomplete="current-password",
            )
            submitted = st.form_submit_button(
                "영업 분석 열기", type="primary", use_container_width=True
            )
        if submitted:
            if service.verify_analytics_password(password):
                st.session_state["analytics_authenticated"] = True
                st.rerun()
            st.error("비밀번호가 올바르지 않습니다.")
    return False


def _reset_password_gate(service: LoungeService) -> bool:
    if st.session_state.get("reset_authenticated") is True:
        return True

    issue = service.reset_password_issue()
    if issue:
        st.error(issue)
        st.caption("Streamlit Secrets에 운영자 비밀번호와 다른 RESET_PASSWORD를 설정해 주세요.")
        return False

    with st.container(key="reset_gate"):
        st.markdown(
            '<div class="analytics-gate-copy">초기화 전용 비밀번호를 입력해 주세요.</div>',
            unsafe_allow_html=True,
        )
        with st.form("reset_password_form", clear_on_submit=True):
            password = st.text_input(
                "초기화 비밀번호",
                type="password",
                placeholder="초기화용 비밀번호 입력",
                autocomplete="current-password",
            )
            submitted = st.form_submit_button(
                "초기화 기능 열기", type="primary", use_container_width=True
            )
        if submitted:
            if service.verify_reset_password(password):
                st.session_state["reset_authenticated"] = True
                st.rerun()
            st.error("비밀번호가 올바르지 않습니다.")
    return False


def _minutes_label(minutes: int) -> str:
    hours, remainder = divmod(max(0, int(minutes)), 60)
    if hours:
        return f"{hours}시간 {remainder}분"
    return f"{remainder}분"


def _hourly_visits_html(rows: list[dict]) -> str:
    if not rows:
        return '<div class="analytics-empty">아직 오늘 입장 기록이 없습니다.</div>'
    maximum = max(row["count"] for row in rows) or 1
    bars = "".join(
        f'<div class="hour-row"><div class="hour-label">{esc(row["hour"])}</div>'
        f'<div class="hour-track"><div class="hour-fill" style="width:{max(8, row["count"] / maximum * 100):.1f}%"></div></div>'
        f'<div class="hour-count">{row["count"]}명</div></div>'
        for row in rows
    )
    return f'<div class="analytics-panel">{bars}</div>'


def _category_split_html(general: int, vip: int) -> str:
    total = general + vip
    general_ratio = general / total * 100 if total else 0
    vip_ratio = 100 - general_ratio if total else 0
    return f"""
    <div class="analytics-panel category-panel">
      <div class="category-summary">
        <div><span class="category-dot general-dot"></span>일반 <strong>{general}명</strong></div>
        <div><span class="category-dot vip-dot"></span>VIP <strong>{vip}명</strong></div>
      </div>
      <div class="category-track">
        <div class="category-general" style="width:{general_ratio:.1f}%"></div>
        <div class="category-vip" style="width:{vip_ratio:.1f}%"></div>
      </div>
      <div class="category-percent"><span>{general_ratio:.1f}%</span><span>{vip_ratio:.1f}%</span></div>
    </div>
    """


def _visit_details_html(visits: list[dict]) -> str:
    if not visits:
        return '<div class="analytics-empty">오늘 방문자 정보가 없습니다.</div>'
    rows = []
    for visit in visits:
        category = "VIP" if visit["category"] == "vip" else "일반"
        status = "입장 중" if visit["status"] == "active" else "퇴장"
        status_class = "active" if visit["status"] == "active" else "exited"
        code_label = f'ID {esc(visit["code"])}'
        rows.append(
            f'<div class="visit-row"><div><div class="visit-name">{esc(visit["name"])}</div>'
            f'<div class="visit-meta">{code_label} · {visit["visit_number"]}/{visit["entry_count"]}회 · {category} · '
            f'{esc(visit["age"])}세 · {esc(visit["phone"])}</div></div>'
            f'<div class="visit-time"><span>입장 {esc(visit["checked_in"])}</span>'
            f'<span>퇴장 {esc(visit["checked_out"])}</span></div>'
            f'<div class="visit-duration">{esc(_minutes_label(visit["duration_minutes"]))}</div>'
            f'<div class="visit-status {status_class}">{status}</div></div>'
        )
    return '<div class="analytics-panel visit-list">' + "".join(rows) + "</div>"


def _render_analytics_panel(service: LoungeService) -> None:
    if not _analytics_password_gate(service):
        return

    st.markdown("## 영업 분석")
    st.caption("오늘의 방문·입퇴장·체류 정보를 집계합니다. 전화번호는 일부만 마스킹해 표시합니다.")

    @st.fragment(run_every=timedelta(seconds=10))
    def analytics_live() -> None:
        stats = service.visit_analytics()
        st.markdown(
            metric_cards(
                [
                    ("오늘 방문", stats["total"]),
                    ("현재 입장", stats["active"]),
                    ("퇴장 완료", stats["exited"]),
                    ("평균 체류시간", _minutes_label(stats["average_duration_minutes"])),
                ]
            ),
            unsafe_allow_html=True,
        )
        left, right = st.columns([1.2, 0.8], gap="large")
        with left:
            st.markdown("### 시간대별 방문자 수")
            st.markdown(_hourly_visits_html(stats["hourly"]), unsafe_allow_html=True)
        with right:
            st.markdown("### VIP·일반 방문 비율")
            st.markdown(
                _category_split_html(stats["general"], stats["vip"]),
                unsafe_allow_html=True,
            )
        st.markdown("### 오늘 방문자별 입퇴장 정보")
        st.caption("평균 체류시간은 퇴장이 완료된 방문만 기준으로 계산됩니다.")
        st.markdown(_visit_details_html(stats["visits"]), unsafe_allow_html=True)

    analytics_live()


def render_analytics(service: LoungeService) -> None:
    """Keep the old analytics URL compatible while routing it through the console gate."""
    st.query_params["view"] = "admin"
    st.query_params["panel"] = "analytics"
    render_admin(service)


def _quick_points_console(service: LoungeService, operator: str) -> None:
    st.markdown(
        '<div class="quick-guide"><strong>앞 수치 + 참가자 ID + 뒤 수치</strong>'
        '<span>입력값은 100배로 반영됩니다. 예: <b>300RT140</b> → 변동 -16,000P · '
        '뒤 수치를 생략한 <b>330RT</b>는 330RT0과 같습니다. 입력 후 Enter</span></div>',
        unsafe_allow_html=True,
    )
    payload = quick_point_input(key="festival_chip_command")
    if payload and payload.get("submission_id") != st.session_state.get("last_chip_submission"):
        st.session_state["last_chip_submission"] = payload.get("submission_id")
        try:
            result = service.quick_adjust_points(str(payload.get("command", "")), operator)
            st.session_state["quick_feedback"] = (
                "success",
                f"{result.display_code} · {result.name}  사용 {result.spent_points:,}P · "
                f"획득 {result.earned_points:,}P · 변동 {result.delta:+,}P  →  현재 {result.balance:,}P",
            )
        except ValueError as exc:
            st.session_state["quick_feedback"] = ("error", str(exc))

    feedback = st.session_state.get("quick_feedback")
    if feedback:
        kind, message = feedback
        if kind == "success":
            st.markdown(f'<div class="quick-result success">{esc(message)}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="quick-result error">{esc(message)}</div>', unsafe_allow_html=True)


def _participant_list(service: LoungeService, operator: str) -> None:
    st.markdown("### 방문 명단")
    search = st.text_input("명단 검색", key="list_search", placeholder="이름·코드·전화번호 뒤 4자리")
    status = st.radio("상태", ["전체", "입장 중", "퇴장"], horizontal=True)
    rows = service.search_participants(search, active_only=status == "입장 중", limit=500)
    if status == "퇴장":
        rows = [row for row in rows if row["status"] == "exited"]
    table = [
        {
            "ID": row["code"] or "—",
            "이름": row["name"],
            "입장 회차": f'{row["visit_number"]}/{row["entry_count"]}',
            "상태": "입장 중" if row["status"] == "active" else "퇴장",
            "포인트": row["points"],
            "입장": service.format_time(row["checked_in_at"], include_date=True),
            "퇴장": service.format_time(row["checked_out_at"], include_date=True),
        }
        for row in rows
    ]
    st.dataframe(table, hide_index=True, use_container_width=True, height=420)
    st.caption(f"검색 결과 {len(rows)}명")

    exited = [row for row in rows if row["status"] == "exited"]
    if exited:
        st.markdown("#### 잘못 처리한 퇴장 복구")
        labels = {
            row["id"]: (
                f"{row['name']} · {row['visit_number']}회차 · "
                f"{service.format_time(row['checked_out_at'], True)}"
            )
            for row in exited
        }
        chosen = st.selectbox("복구할 참가자", list(labels), format_func=lambda value: labels[value])
        if st.button("입장 중 상태로 복구"):
            try:
                service.reopen_participant(chosen, operator)
                st.success("퇴장 기록이 복구되었습니다.")
            except ValueError as exc:
                st.error(str(exc))
