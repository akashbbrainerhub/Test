import os
from datetime import date, datetime, time
from typing import Any

import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_API_URL = os.getenv("FASTAPI_BASE_URL", "http://127.0.0.1:8000")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("STREAMLIT_API_TIMEOUT", "15"))
STATUS_OPTIONS = ["pending", "in_progress", "completed"]
SORT_OPTIONS = ["created_at", "deadline", "title", "status"]


@st.cache_resource
def get_api_session() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.4,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST", "PUT", "DELETE"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def init_state() -> None:
    defaults = {
        "api_url": DEFAULT_API_URL,
        "access_token": None,
        "current_user": None,
        "status_filter": "all",
        "sort_by": "created_at",
        "sort_order": "desc",
        "page": 1,
        "size": 10,
        "use_deadline_from": False,
        "use_deadline_to": False,
        "deadline_from": None,
        "deadline_to": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def build_url(path: str) -> str:
    return f"{st.session_state.api_url.rstrip('/')}{path}"


def parse_api_error(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"HTTP {response.status_code}: {response.text[:250]}"

    detail = payload.get("detail", payload)
    if isinstance(detail, list):
        return "; ".join(str(item) for item in detail)
    if isinstance(detail, dict):
        return str(detail)
    return str(detail)


def api_request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    **kwargs: Any,
) -> tuple[bool, Any, str]:
    session = get_api_session()
    headers = kwargs.pop("headers", {})

    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = session.request(
            method=method,
            url=build_url(path),
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers=headers,
            **kwargs,
        )
    except requests.RequestException as exc:
        return False, None, f"Network error: {exc}"

    if response.status_code >= 400:
        return False, None, parse_api_error(response)

    if response.status_code == 204:
        return True, None, ""

    try:
        return True, response.json(), ""
    except ValueError:
        return True, response.text, ""


def register_user(username: str, password: str) -> tuple[bool, str]:
    ok, _, error = api_request("POST", "/auth/register", json={"username": username, "password": password})
    if not ok:
        return False, error
    return True, "Registration successful. You can now log in."


def login_user(username: str, password: str) -> tuple[bool, str]:
    ok, payload, error = api_request(
        "POST",
        "/auth/token",
        data={"username": username, "password": password, "grant_type": "password"},
    )
    if not ok:
        return False, error

    access_token = payload.get("access_token")
    if not access_token:
        return False, "Login failed: access token was not returned by the API"

    st.session_state.access_token = access_token
    return refresh_current_user()


def refresh_current_user() -> tuple[bool, str]:
    ok, payload, error = api_request("GET", "/auth/me", token=st.session_state.access_token)
    if not ok:
        st.session_state.access_token = None
        st.session_state.current_user = None
        return False, error

    st.session_state.current_user = payload
    return True, ""


def logout() -> None:
    st.session_state.access_token = None
    st.session_state.current_user = None


def to_api_datetime(value: date, end_of_day: bool = False) -> str:
    dt_time = time(23, 59, 59) if end_of_day else time(0, 0, 0)
    return datetime.combine(value, dt_time).isoformat()


def combine_date_time(deadline_date: date, deadline_time: time) -> datetime:
    return datetime.combine(deadline_date, deadline_time)


def parse_iso_datetime(value: str) -> datetime:
    cleaned = value.replace("Z", "+00:00")
    return datetime.fromisoformat(cleaned)


def fetch_tasks() -> tuple[bool, dict[str, Any] | None, str]:
    params: dict[str, Any] = {
        "page": st.session_state.page,
        "size": st.session_state.size,
        "sort_by": st.session_state.sort_by,
        "sort_order": st.session_state.sort_order,
    }

    if st.session_state.status_filter != "all":
        params["status"] = st.session_state.status_filter

    if st.session_state.deadline_from:
        params["deadline_from"] = to_api_datetime(st.session_state.deadline_from)

    if st.session_state.deadline_to:
        params["deadline_to"] = to_api_datetime(st.session_state.deadline_to, end_of_day=True)

    ok, payload, error = api_request("GET", "/tasks", token=st.session_state.access_token, params=params)
    if not ok:
        return False, None, error
    return True, payload, ""


def render_auth_page() -> None:
    st.subheader("Account")
    login_tab, register_tab = st.tabs(["Login", "Register"])

    with login_tab:
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            ok, message = login_user(username.strip(), password)
            if ok:
                st.success("Logged in successfully")
                st.rerun()
            else:
                st.error(message)

    with register_tab:
        with st.form("register_form", clear_on_submit=False):
            username = st.text_input("New username", key="register_username")
            password = st.text_input("New password", type="password", key="register_password")
            submitted = st.form_submit_button("Create Account", use_container_width=True)

        if submitted:
            ok, message = register_user(username.strip(), password)
            if ok:
                st.success(message)
            else:
                st.error(message)


def render_sidebar() -> None:
    with st.sidebar:
        st.header("Settings")
        api_url_input = st.text_input("FastAPI base URL", value=st.session_state.api_url)
        st.session_state.api_url = api_url_input.strip() or DEFAULT_API_URL

        user = st.session_state.current_user
        if user:
            st.success(f"Signed in as {user['username']} ({user['role']})")
            if st.button("Sign Out", use_container_width=True):
                logout()
                st.rerun()

        st.divider()
        st.subheader("Task Filters")

        st.session_state.status_filter = st.selectbox(
            "Status",
            options=["all"] + STATUS_OPTIONS,
            index=( ["all"] + STATUS_OPTIONS ).index(st.session_state.status_filter)
            if st.session_state.status_filter in ["all"] + STATUS_OPTIONS
            else 0,
        )

        st.session_state.sort_by = st.selectbox(
            "Sort by",
            options=SORT_OPTIONS,
            index=SORT_OPTIONS.index(st.session_state.sort_by)
            if st.session_state.sort_by in SORT_OPTIONS
            else 0,
        )

        st.session_state.sort_order = st.selectbox(
            "Sort order",
            options=["desc", "asc"],
            index=0 if st.session_state.sort_order == "desc" else 1,
        )

        st.session_state.size = st.slider("Page size", min_value=1, max_value=100, value=st.session_state.size)

        st.session_state.use_deadline_from = st.checkbox(
            "Use deadline from",
            value=st.session_state.use_deadline_from,
            key="use_deadline_from_input",
        )
        if st.session_state.use_deadline_from:
            default_from = st.session_state.deadline_from or date.today()
            st.session_state.deadline_from = st.date_input("Deadline from", value=default_from)
        else:
            st.session_state.deadline_from = None

        st.session_state.use_deadline_to = st.checkbox(
            "Use deadline to",
            value=st.session_state.use_deadline_to,
            key="use_deadline_to_input",
        )
        if st.session_state.use_deadline_to:
            default_to = st.session_state.deadline_to or date.today()
            st.session_state.deadline_to = st.date_input("Deadline to", value=default_to)
        else:
            st.session_state.deadline_to = None

        if st.button("Refresh Tasks", use_container_width=True):
            st.rerun()


def render_create_task() -> None:
    with st.expander("Create Task", expanded=True):
        with st.form("create_task_form"):
            title = st.text_input("Title")
            description = st.text_area("Description", height=120)
            status = st.selectbox("Status", options=STATUS_OPTIONS, index=0)
            deadline_date = st.date_input("Deadline date", value=date.today())
            deadline_time = st.time_input(
                "Deadline time",
                value=datetime.now().time().replace(second=0, microsecond=0),
            )
            submitted = st.form_submit_button("Create", use_container_width=True)

        if submitted:
            deadline = combine_date_time(deadline_date, deadline_time)
            payload = {
                "title": title.strip(),
                "description": description.strip(),
                "status": status,
                "deadline": deadline.isoformat(),
            }
            ok, _, error = api_request("POST", "/tasks", token=st.session_state.access_token, json=payload)
            if ok:
                st.success("Task created")
                st.rerun()
            else:
                st.error(error)


def render_task_row(task: dict[str, Any]) -> None:
    deadline_dt = parse_iso_datetime(task["deadline"])
    created_dt = parse_iso_datetime(task["created_at"])

    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"### {task['title']}")
            st.write(task["description"])
        with col2:
            st.caption("Status")
            st.write(task["status"])
            st.caption("Deadline")
            st.write(deadline_dt.strftime("%Y-%m-%d %H:%M"))
        with col3:
            st.caption("Created")
            st.write(created_dt.strftime("%Y-%m-%d %H:%M"))
            st.caption("Task ID")
            st.code(task["id"], language=None)

        with st.expander("Edit Task"):
            with st.form(f"edit_{task['id']}"):
                new_title = st.text_input("Title", value=task["title"], key=f"title_{task['id']}")
                new_description = st.text_area(
                    "Description",
                    value=task["description"],
                    key=f"desc_{task['id']}",
                    height=120,
                )
                new_status = st.selectbox(
                    "Status",
                    options=STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(task["status"]),
                    key=f"status_{task['id']}",
                )
                new_deadline_date = st.date_input(
                    "Deadline date",
                    value=deadline_dt.date(),
                    key=f"deadline_date_{task['id']}",
                )
                new_deadline_time = st.time_input(
                    "Deadline time",
                    value=deadline_dt.time().replace(second=0, microsecond=0),
                    key=f"deadline_time_{task['id']}",
                )

                update_submitted = st.form_submit_button("Save Changes", use_container_width=True)

                if update_submitted:
                    new_deadline = combine_date_time(new_deadline_date, new_deadline_time)
                    update_payload = {
                        "title": new_title.strip(),
                        "description": new_description.strip(),
                        "status": new_status,
                        "deadline": new_deadline.isoformat(),
                    }
                    ok, _, error = api_request(
                        "PUT",
                        f"/tasks/{task['id']}",
                        token=st.session_state.access_token,
                        json=update_payload,
                    )
                    if ok:
                        st.success("Task updated")
                        st.rerun()
                    else:
                        st.error(error)

        if st.button("Delete Task", key=f"delete_{task['id']}", use_container_width=False):
            ok, _, error = api_request("DELETE", f"/tasks/{task['id']}", token=st.session_state.access_token)
            if ok:
                st.success("Task deleted")
                st.rerun()
            else:
                st.error(error)


def render_tasks() -> None:
    ok, payload, error = fetch_tasks()
    if not ok:
        st.error(error)
        return

    assert payload is not None
    items = payload.get("items", [])
    total = int(payload.get("total", 0))
    page = int(payload.get("page", 1))
    size = int(payload.get("size", st.session_state.size))

    pending = sum(1 for item in items if item["status"] == "pending")
    in_progress = sum(1 for item in items if item["status"] == "in_progress")
    completed = sum(1 for item in items if item["status"] == "completed")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total (filter)", total)
    m2.metric("Pending", pending)
    m3.metric("In Progress", in_progress)
    m4.metric("Completed", completed)

    st.caption(f"Showing page {page} with size {size}")

    if not items:
        st.info("No tasks found for the current filters.")
    else:
        for task in items:
            render_task_row(task)

    max_page = max(1, (total + size - 1) // size)
    prev_col, page_col, next_col = st.columns([1, 2, 1])

    with prev_col:
        if st.button("Previous", disabled=page <= 1, use_container_width=True):
            st.session_state.page = max(1, page - 1)
            st.rerun()

    with page_col:
        st.number_input(
            "Page",
            min_value=1,
            max_value=max_page,
            value=page,
            step=1,
            key="page_number_input",
        )
        if st.button("Go", use_container_width=True):
            st.session_state.page = int(st.session_state.page_number_input)
            st.rerun()

    with next_col:
        if st.button("Next", disabled=page >= max_page, use_container_width=True):
            st.session_state.page = min(max_page, page + 1)
            st.rerun()


def apply_styles() -> None:
    st.markdown(
        """
        <style>
            .stApp {
                background:
                    radial-gradient(circle at 0% 0%, #f6f8ff 0, transparent 30%),
                    radial-gradient(circle at 100% 100%, #fff5e8 0, transparent 28%),
                    #f9fafc;
            }
            h1, h2, h3 {
                letter-spacing: -0.02em;
            }
            .block-container {
                padding-top: 1.2rem;
                padding-bottom: 2rem;
                max-width: 1150px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="Task Command Center", layout="wide")
    init_state()
    apply_styles()

    st.title("Task Command Center")
    st.caption("Production-ready Streamlit frontend for your FastAPI task management backend")

    render_sidebar()

    if not st.session_state.access_token:
        render_auth_page()
        return

    if st.session_state.current_user is None:
        ok, error = refresh_current_user()
        if not ok:
            st.error(f"Session expired: {error}")
            render_auth_page()
            return

    render_create_task()
    render_tasks()


if __name__ == "__main__":
    main()
