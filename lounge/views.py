from __future__ import annotations

import html

import pandas as pd
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
              <div class="ticket-memory-label">반드시 기억하세요</div>
              <div class="ticket-code">{esc(ticket["code"])}</div>
              <div class="ticket-memory-title">이 두 글자가 나의 참가자 ID입니다</div>
              <div class="ticket-memory-copy">활동 포인트를 받을 때마다 운영진에게 이 ID를 말해 주세요.</div>
              <div style="color:#a5b6ae;margin-top:.75rem">시작 포인트 {ticket["points"]:,} P</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.warning(f"중요: 나의 ID는 {ticket['code']}입니다. 화면을 닫기 전에 반드시 기억해 주세요.")
        if st.button("다음 방문자 등록", type="primary", use_container_width=True):
            del st.session_state["last_ticket"]
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
                        "<div class='kiosk-section-copy'>연락처와 안내받은 참가 유형을 선택해 주세요.</div>",
                        unsafe_allow_html=True,
                    )
                    phone = st.text_input("전화번호 *", max_chars=15, placeholder="010-1234-5678")
                    category_label = st.radio(
                        "참가 유형 *",
                        ["일반", "VIP"],
                        horizontal=True,
                        help="VIP 여부는 운영진 안내에 따라 선택하세요.",
                    )
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
                category="vip" if category_label == "VIP" else "general",
                privacy_consent=True,
                leaderboard_opt_in=True,
            )
            st.session_state["last_ticket"] = {
                "name": name.strip(),
                "code": result.display_code,
                "points": result.starting_points,
            }
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


def leaderboard_html(rows: list[dict]) -> str:
    if not rows:
        return "<div class='panel-card' style='color:#a5b6ae'>아직 순위 데이터가 없습니다.</div>"
    body = []
    for index, row in enumerate(rows, 1):
        body.append(
            f'<div class="rank-row"><div class="rank-number">{index:02d}</div>'
            f'<div><div class="rank-name">{esc(row["name"])}</div>'
            f'<div class="rank-code">ID&nbsp; {esc(row["code"])}</div></div>'
            f'<div class="rank-points">{row["points"]:,} P</div></div>'
        )
    return "<div class='panel-card'>" + "".join(body) + "</div>"


def podium_html(rows: list[dict]) -> str:
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
        '<div class="podium-title"><span>TOP 3</span> · LIVE RANKING</div>'
        '<div class="podium-grid">'
        + podium_place(2)
        + podium_place(1)
        + podium_place(3)
        + "</div></div>"
    )


def render_board(service: LoungeService) -> None:
    top_brand(service, "LIVE OPERATIONS BOARD")
    st.markdown(
        "<div style='color:#a5b6ae'><span class='live-dot'></span>2초마다 자동 갱신</div>",
        unsafe_allow_html=True,
    )

    @st.fragment(run_every="2s")
    def live_board() -> None:
        stats = service.dashboard()
        podium_column, ranking_column = st.columns([1.35, 0.65], gap="large", vertical_alignment="top")
        with podium_column:
            with st.container(key="board_podium"):
                st.markdown(podium_html(stats["leaderboard"][:3]), unsafe_allow_html=True)
        with ranking_column:
            with st.container(key="board_ranking"):
                st.markdown(
                    "<div class='ranking-heading'><span>ALL PLAYERS</span>"
                    "<strong>현재 포인트 순위</strong></div>"
                    + leaderboard_html(stats["leaderboard"]),
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


def render_admin(service: LoungeService) -> None:
    top_brand(service, "OPERATIONS CONSOLE")
    operator = "festival_staff"
    panel = str(st.query_params.get("panel", "menu")).lower()

    if panel == "chips":
        st.markdown("## 전산 칩 관리")
        _quick_points_console(service, operator)
        st.link_button("운영자 메뉴로 돌아가기", "?view=admin")
    elif panel == "checkout":
        _checkout_console(service, operator)
        st.link_button("운영자 메뉴로 돌아가기", "?view=admin")
    elif panel == "visitors":
        _participant_list(service, operator)
        st.link_button("운영자 메뉴로 돌아가기", "?view=admin")
    else:
        st.markdown("## 운영자 콘솔")
        columns = st.columns(3)
        menu_items = [
            (
                "01",
                "전산 칩 관리",
                "두 글자 ID와 포인트를 입력해 가장 빠르게 기록합니다.",
                "전산 칩 관리 열기",
                "?view=admin&panel=chips",
            ),
            (
                "02",
                "퇴장 처리",
                "참가자를 검색하고 최종 보유 포인트와 퇴장을 기록합니다.",
                "퇴장 처리 열기",
                "?view=admin&panel=checkout",
            ),
            (
                "03",
                "방문 명단",
                "현재 입장·퇴장 상태와 포인트를 확인합니다.",
                "방문 명단 열기",
                "?view=admin&panel=visitors",
            ),
        ]
        for column, (number, title, copy, label, href) in zip(columns, menu_items, strict=True):
            with column:
                st.markdown(
                    f'<div class="mode-card"><div class="mode-num">{number}</div>'
                    f'<div class="mode-title">{esc(title)}</div>'
                    f'<div class="mode-copy">{esc(copy)}</div></div>',
                    unsafe_allow_html=True,
                )
                st.link_button(label, href, use_container_width=True)
    footer()


def _quick_points_console(service: LoungeService, operator: str) -> None:
    st.markdown(
        '<div class="quick-guide"><strong>두 글자 ID + 받은 포인트</strong>'
        '<span>입력창은 자동으로 선택됩니다. 예: <b>RT70</b> 입력 후 Enter</span></div>',
        unsafe_allow_html=True,
    )
    payload = quick_point_input(key="festival_chip_command")
    if payload and payload.get("submission_id") != st.session_state.get("last_chip_submission"):
        st.session_state["last_chip_submission"] = payload.get("submission_id")
        try:
            result = service.quick_adjust_points(str(payload.get("command", "")), operator)
            st.session_state["quick_feedback"] = (
                "success",
                f"{result.display_code} · {result.name}  {result.delta:+,}P  →  현재 {result.balance:,}P",
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
    rows = service.search_participants(search, active_only=status == "입장 중", limit=500)
    if status == "퇴장":
        rows = [row for row in rows if row["status"] == "exited"]
    table = pd.DataFrame(
        [
            {
                "ID": row["code"],
                "이름": row["name"],
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
        st.markdown("#### 잘못 처리한 퇴장 복구")
        labels = {
            row["id"]: f"{row['name']} · {row['code']} · {service.format_time(row['checked_out_at'], True)}"
            for row in exited
        }
        chosen = st.selectbox("복구할 참가자", list(labels), format_func=lambda value: labels[value])
        if st.button("입장 중 상태로 복구"):
            try:
                service.reopen_participant(chosen, operator)
                st.success("퇴장 기록이 복구되었습니다.")
            except ValueError as exc:
                st.error(str(exc))
