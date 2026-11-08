from __future__ import annotations

import html
import os
import re
import sqlite3
from datetime import date, datetime, time
from pathlib import Path

import streamlit as st

APP_TITLE = "Rommaka Praxis"
DB_PATH = Path(os.environ.get("RMP_DB_PATH", "data/rommaka_praxis.sqlite3"))
st.set_page_config(page_title=APP_TITLE, page_icon="📋", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
.block-container{padding-top:1.2rem;padding-bottom:2rem;max-width:1200px}
.activity-meta{color:#667085;font-size:.9rem}
@media(max-width:600px){.block-container{padding-left:1rem;padding-right:1rem}h1{font-size:1.7rem!important}}
</style>""", unsafe_allow_html=True)


def connect_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS activities(
        id INTEGER PRIMARY KEY AUTOINCREMENT, activity TEXT NOT NULL,
        sector TEXT NOT NULL DEFAULT '', subsector TEXT NOT NULL DEFAULT '',
        location TEXT NOT NULL DEFAULT '', scheduled_at TEXT NOT NULL,
        steps TEXT NOT NULL DEFAULT '', comment TEXT NOT NULL DEFAULT '',
        is_daily INTEGER NOT NULL DEFAULT 1, completed INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
    db.commit()
    return db


conn = connect_db()


def load_activities():
    return conn.execute("SELECT * FROM activities ORDER BY scheduled_at DESC,id DESC").fetchall()


def as_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return datetime.now().replace(second=0, microsecond=0)


def is_point_eligible(row) -> bool:
    """Points require the explicit completed check and inclusion in the daily list."""
    return bool(row["completed"] and row["is_daily"])


def points_for_day(day: date, activities=None) -> int:
    activities = load_activities() if activities is None else activities
    return sum(1 for r in activities if is_point_eligible(r) and as_datetime(r["scheduled_at"]).date() == day)


def distinct_values(field: str) -> list[str]:
    if field not in {"sector", "subsector"}:
        return []
    return [r[0] for r in conn.execute(
        f"SELECT DISTINCT {field} FROM activities WHERE trim({field})<>'' ORDER BY {field}"
    ).fetchall()]


def show_text_with_links(value: str) -> None:
    escaped = html.escape(value or "").replace("\n", "<br>")
    pattern = re.compile(r"https?://[^\s&lt;&gt;]+", re.IGNORECASE)

    def anchor(match: re.Match[str]) -> str:
        url = match.group(0)
        suffix = ""
        while url and url[-1] in ".,;:!?":
            suffix, url = url[-1] + suffix, url[:-1]
        if url.endswith(")") and url.count("(") < url.count(")"):
            suffix, url = ")" + suffix, url[:-1]
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{url}</a>{suffix}'

    st.markdown(pattern.sub(anchor, escaped), unsafe_allow_html=True)


def matches(row, query: str = "") -> bool:
    text = " ".join(str(row[k]) for k in ("activity", "sector", "subsector", "location", "steps", "comment"))
    return not query or query.casefold() in text.casefold()


def show_activities(items, empty_message="Nenhuma atividade encontrada.") -> None:
    if not items:
        st.info(empty_message)
        return
    for row in items:
        rid = int(row["id"])
        scheduled = as_datetime(row["scheduled_at"])
        title, edit_col, delete_col = st.columns([8, 1, 1])
        with title:
            status = "✅" if row["completed"] else "⬜"
            daily = " · 📌 Lista diária" if row["is_daily"] else ""
            st.markdown(
                f"**{status} {row['activity']}**  \n<span class='activity-meta'>{scheduled:%d/%m/%Y %H:%M} · {row['sector'] or 'Sem setor'} / {row['subsector'] or 'Sem subsetor'} · {row['location'] or 'Sem local'}{daily}</span>",
                unsafe_allow_html=True,
            )
        with edit_col:
            if st.button("Editar", key=f"edit_{rid}", use_container_width=True):
                st.session_state["editing_id"] = rid
                st.rerun()
        with delete_col:
            if st.button("Excluir", key=f"delete_{rid}", use_container_width=True):
                st.session_state["confirm_delete"] = rid
        if st.session_state.get("confirm_delete") == rid:
            st.warning(f"Excluir definitivamente ‘{row['activity']}’?")
            yes, no = st.columns(2)
            with yes:
                if st.button("Confirmar exclusão", key=f"confirm_{rid}", type="primary"):
                    conn.execute("DELETE FROM activities WHERE id=?", (rid,))
                    conn.commit()
                    st.session_state.pop("confirm_delete", None)
                    if st.session_state.get("editing_id") == rid:
                        st.session_state.pop("editing_id", None)
                    st.rerun()
            with no:
                if st.button("Cancelar", key=f"cancel_delete_{rid}"):
                    st.session_state.pop("confirm_delete", None)
                    st.rerun()
        with st.expander("Detalhes e links"):
            if row["steps"]:
                st.markdown("**Passo a passo**")
                show_text_with_links(row["steps"])
            if row["comment"]:
                st.markdown("**Comentário**")
                show_text_with_links(row["comment"])
            if not row["steps"] and not row["comment"]:
                st.caption("Sem detalhes adicionais.")
        st.divider()


# Daily score is visible in the upper-right corner on all tabs.
heading, score = st.columns([5, 1.3], vertical_alignment="center")
with heading:
    st.title("📋 Rommaka Praxis")
    st.caption("Gestão de atividades, listas e pontuação — adaptado para telemóvel.")
rows = load_activities()
with score:
    st.metric("Pontos de hoje", points_for_day(date.today(), rows))

editing_id = st.session_state.get("editing_id")
editing = next((r for r in rows if int(r["id"]) == editing_id), None)
if editing_id and editing is None:
    st.session_state.pop("editing_id", None)
    editing_id = None

with st.container(border=True):
    st.subheader("Editar atividade" if editing else "Nova atividade")
    form_token = f"edit_{editing_id}" if editing else f"new_{st.session_state.get('form_version', 0)}"
    with st.form(f"activity_form_{form_token}"):
        daily = st.checkbox("📌 Incluir na lista diária", value=bool(editing["is_daily"]) if editing else True, key=f"daily_{form_token}")
        activity = st.text_input("Atividade *", value=editing["activity"] if editing else "", key=f"activity_{form_token}", placeholder="Ex.: Preparar relatório")
        c1, c2, c3 = st.columns(3)
        with c1:
            sector = st.text_input("Setor", value=editing["sector"] if editing else "", key=f"sector_{form_token}", placeholder="Ex.: Base")
        with c2:
            subsector = st.text_input("Subsetor", value=editing["subsector"] if editing else "", key=f"subsector_{form_token}", placeholder="Ex.: Operações")
        with c3:
            location = st.text_input("Local", value=editing["location"] if editing else "", key=f"location_{form_token}", placeholder="Ex.: Polo Alfa")
        dt = as_datetime(editing["scheduled_at"]) if editing else datetime.now().replace(second=0, microsecond=0)
        date_col, time_col = st.columns(2)
        with date_col:
            scheduled_date = st.date_input("Data", value=dt.date(), key=f"date_{form_token}")
        with time_col:
            scheduled_time = st.time_input("Horário", value=dt.time().replace(second=0, microsecond=0), key=f"time_{form_token}")
        s_col, c_col = st.columns(2)
        with s_col:
            steps = st.text_area("Passo a passo", value=editing["steps"] if editing else "", key=f"steps_{form_token}", height=120, placeholder="Cole aqui texto ou links.")
        with c_col:
            comment = st.text_area("Comentário", value=editing["comment"] if editing else "", key=f"comment_{form_token}", height=120, placeholder="Observações e links.")
        completed = st.checkbox("✅ Realizado (+1 ponto diário)", value=bool(editing["completed"]) if editing else False, key=f"completed_{form_token}", help="A pontuação só conta quando este campo está marcado e a atividade está na lista diária.")
        save_col, cancel_col = st.columns(2)
        with save_col:
            save = st.form_submit_button("💾 Salvar" if editing else "💾 Salvar e limpar campos", type="primary", use_container_width=True)
        with cancel_col:
            cancel = st.form_submit_button("Cancelar edição" if editing else "Limpar formulário", use_container_width=True)

    if cancel:
        if editing:
            st.session_state.pop("editing_id", None)
        st.session_state["form_version"] = st.session_state.get("form_version", 0) + 1
        st.rerun()
    if save:
        if not activity.strip():
            st.error("Informe o nome da atividade antes de salvar.")
        else:
            now = datetime.now().isoformat(timespec="seconds")
            values = (
                activity.strip(), sector.strip(), subsector.strip(), location.strip(),
                datetime.combine(scheduled_date, scheduled_time).isoformat(timespec="minutes"),
                steps.strip(), comment.strip(), int(daily), int(completed), now,
            )
            if editing:
                conn.execute("""UPDATE activities SET activity=?,sector=?,subsector=?,location=?,scheduled_at=?,steps=?,comment=?,is_daily=?,completed=?,updated_at=? WHERE id=?""", (*values, int(editing_id)))
                st.session_state.pop("editing_id", None)
                st.success("Atividade atualizada.")
            else:
                conn.execute("""INSERT INTO activities(activity,sector,subsector,location,scheduled_at,steps,comment,is_daily,completed,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)""", values)
                st.session_state["form_version"] = st.session_state.get("form_version", 0) + 1
                st.success("Atividade salva; os campos foram limpos.")
            conn.commit()
            st.rerun()

st.markdown("### Listas e relatórios")
tabs = st.tabs(["📅 Lista diária", "🗂️ Atividades", "🏢 Setores", "🧩 Subsetores", "🗓️ Por data", "⭐ Pontos", "📊 Relatórios"])
with tabs[0]:
    today = date.today()
    st.subheader(f"Atividades de hoje — {today:%d/%m/%Y}")
    show_activities([r for r in rows if r["is_daily"] and as_datetime(r["scheduled_at"]).date() == today])
with tabs[1]:
    st.subheader("Todas as atividades")
    query = st.text_input("Pesquisar atividade, setor, subsetor, local ou texto", key="all_search")
    show_activities([r for r in rows if matches(r, query)])
with tabs[2]:
    st.subheader("Lista por setor")
    sectors = distinct_values("sector")
    if sectors:
        selected = st.selectbox("Selecione um setor", sectors, key="sector_filter")
        show_activities([r for r in rows if r["sector"] == selected])
    else:
        st.info("Os setores aparecem aqui depois de cadastrar atividades com setor.")
with tabs[3]:
    st.subheader("Lista por subsetor")
    subsets = distinct_values("subsector")
    if subsets:
        selected = st.selectbox("Selecione um subsetor", subsets, key="subsector_filter")
        show_activities([r for r in rows if r["subsector"] == selected])
    else:
        st.info("Os subsetores aparecem aqui depois de cadastrá-los nas atividades.")
with tabs[4]:
    st.subheader("Lista por data")
    selected_date = st.date_input("Escolha uma data", value=date.today(), key="date_filter")
    show_activities([r for r in rows if as_datetime(r["scheduled_at"]).date() == selected_date])
with tabs[5]:
    st.subheader("Pontuação")
    st.caption("Cada atividade realizada que está na lista diária vale 1 ponto. A pontuação só conta quando ‘Realizado’ está marcado. Não é obrigatório preencher setor ou subsetor para pontuar.")
    score_tabs = st.tabs(["Dia", "Mês", "Ano"])
    with score_tabs[0]:
        chosen_day = st.date_input("Dia", value=date.today(), key="points_day")
        st.metric(f"Pontos em {chosen_day:%d/%m/%Y}", points_for_day(chosen_day, rows))
    years = sorted({as_datetime(r["scheduled_at"]).year for r in rows} | {date.today().year}, reverse=True)
    with score_tabs[1]:
        mcol, ycol = st.columns(2)
        with mcol:
            chosen_month = st.selectbox("Mês", range(1, 13), index=date.today().month - 1, format_func=lambda m: date(2000, m, 1).strftime("%B"), key="points_month")
        with ycol:
            month_year = st.selectbox("Ano", years, key="points_month_year")
        count = sum(1 for r in rows if is_point_eligible(r) and (d := as_datetime(r["scheduled_at"])).year == month_year and d.month == chosen_month)
        st.metric(f"Pontos no mês — {chosen_month:02d}/{month_year}", count)
    with score_tabs[2]:
        chosen_year = st.selectbox("Ano", years, key="points_year")
        count = sum(1 for r in rows if is_point_eligible(r) and as_datetime(r["scheduled_at"]).year == chosen_year)
        st.metric(f"Pontos em {chosen_year}", count)
        monthly = []
        for month in range(1, 13):
            total = sum(1 for r in rows if is_point_eligible(r) and (d := as_datetime(r["scheduled_at"])).year == chosen_year and d.month == month)
            monthly.append({"Mês": date(2000, month, 1).strftime("%B").capitalize(), "Pontos": total})
        st.dataframe(monthly, use_container_width=True, hide_index=True)
with tabs[6]:
    st.subheader("Relatório por setor e mês")
    st.caption("Resumo das atividades e pontos do mês selecionado, agrupado por setor e subsetor. Atividades sem setor também aparecem.")
    report_c1, report_c2 = st.columns(2)
    with report_c1:
        report_month = st.selectbox("Mês do relatório", range(1, 13), index=date.today().month - 1, format_func=lambda m: date(2000, m, 1).strftime("%B").capitalize(), key="report_month")
    with report_c2:
        report_year = st.selectbox("Ano do relatório", years, key="report_year")
    report_sector_options = ["Todos os setores"] + distinct_values("sector")
    report_sector = st.selectbox("Filtrar setor", report_sector_options, key="report_sector")
    month_rows = [r for r in rows if (d := as_datetime(r["scheduled_at"])).year == report_year and d.month == report_month and (report_sector == "Todos os setores" or r["sector"] == report_sector)]
    eligible_month_rows = [r for r in month_rows if is_point_eligible(r)]
    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("Atividades no mês", len(month_rows))
    metric2.metric("Realizadas", sum(bool(r["completed"]) for r in month_rows))
    metric3.metric("Pontos", len(eligible_month_rows))
    summary: dict[tuple[str, str], dict[str, int]] = {}
    for r in month_rows:
        key = (r["sector"].strip() or "Sem setor", r["subsector"].strip() or "Sem subsetor")
        summary.setdefault(key, {"Atividades": 0, "Realizadas": 0, "Pontos": 0})
        summary[key]["Atividades"] += 1
        summary[key]["Realizadas"] += int(bool(r["completed"]))
        summary[key]["Pontos"] += int(is_point_eligible(r))
    if summary:
        report_data = [{"Setor": sector_name, "Subsetor": sub_name, **values} for (sector_name, sub_name), values in sorted(summary.items())]
        st.dataframe(report_data, use_container_width=True, hide_index=True)
        st.markdown("**Atividades incluídas no relatório**")
        show_activities(month_rows)
    else:
        st.info("Não há atividades para o setor e mês selecionados.")

with st.sidebar:
    st.header("Rommaka Praxis")
    st.caption("Setores e subsetores são agrupados pelos campos das atividades. Edite uma atividade para alterar a classificação.")
    st.markdown(f"**Base de dados:** `{DB_PATH}`")
    st.markdown("Para persistir no Google Drive, configure `RMP_DB_PATH` para um caminho dentro de `drive/MyDrive` antes de iniciar o app.")
