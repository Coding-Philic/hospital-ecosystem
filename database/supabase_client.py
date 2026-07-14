"""
MediFlow AI — Supabase Client
==============================
Singleton Supabase client initialization and auth helper functions.
Uses service role key for server-side operations (bypasses RLS when needed).
Session persistence via browser cookies so users stay logged in after refresh.

MULTI-USER SAFETY:
- The admin client (@st.cache_resource) is safely shared — it uses a service
  role key and never holds per-user auth state.
- Auth operations (sign_in, set_session, sign_out) use FRESH, non-cached
  clients so one user's session never leaks to another.
"""

import streamlit as st
from supabase import create_client, Client
from config import config


# ── Cookie key constants ───────────────────────────────────────
COOKIE_ACCESS_TOKEN = "mediflow_access_token"
COOKIE_REFRESH_TOKEN = "mediflow_refresh_token"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


def _get_supabase_credentials() -> tuple:
    """
    Resolve Supabase URL and anon key from env or Streamlit secrets.
    Returns (url, key) tuple.
    """
    if config.SUPABASE_URL and config.SUPABASE_KEY:
        return config.SUPABASE_URL, config.SUPABASE_KEY
    try:
        return st.secrets["supabase"]["SUPABASE_URL"], st.secrets["supabase"]["SUPABASE_KEY"]
    except Exception:
        st.error("⚠️ Supabase credentials not configured. Please update `.env` or `.streamlit/secrets.toml`.")
        st.stop()
        return None, None


@st.cache_resource
def get_supabase_client() -> Client:
    """
    Initialize and return a cached Supabase client (anon key).
    WARNING: Do NOT call auth methods (sign_in, set_session, sign_out)
    on this client — use _create_fresh_auth_client() instead.
    This client is shared across ALL users.
    """
    url, key = _get_supabase_credentials()
    if not url:
        return None
    return create_client(url, key)


def _create_fresh_auth_client() -> Client:
    """
    Create a FRESH, non-cached Supabase client for per-user auth operations.
    Each call returns a new instance so auth state (sign_in, set_session)
    is isolated per user and never leaks between sessions.
    """
    url, key = _get_supabase_credentials()
    if not url:
        return None
    return create_client(url, key)


@st.cache_resource
def get_supabase_admin_client() -> Client:
    """
    Initialize and return a cached Supabase client with service role key.
    Bypasses RLS — use only for admin/server operations.
    """
    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_KEY:
        try:
            url = st.secrets["supabase"]["SUPABASE_URL"]
            key = st.secrets["supabase"]["SUPABASE_SERVICE_KEY"]
        except Exception:
            st.error("⚠️ Supabase service key not configured.")
            st.stop()
            return None
    else:
        url = config.SUPABASE_URL
        key = config.SUPABASE_SERVICE_KEY

    return create_client(url, key)


# ── Cookie-Based Session Persistence ──────────────────────────

def save_session_to_cookies(cookie_controller, session):
    """
    Save Supabase session tokens to browser cookies.
    Called after successful sign-in.
    """
    try:
        if session and hasattr(session, "access_token") and hasattr(session, "refresh_token"):
            cookie_controller.set(
                COOKIE_ACCESS_TOKEN,
                session.access_token,
                max_age=COOKIE_MAX_AGE,
                path="/",
            )
            cookie_controller.set(
                COOKIE_REFRESH_TOKEN,
                session.refresh_token,
                max_age=COOKIE_MAX_AGE,
                path="/",
            )
    except Exception:
        pass  # Cookie write failure is non-critical


def clear_session_cookies(cookie_controller):
    """
    Remove session cookies from the browser.
    Called on sign-out.
    """
    try:
        cookie_controller.remove(COOKIE_ACCESS_TOKEN, path="/")
        cookie_controller.remove(COOKIE_REFRESH_TOKEN, path="/")
    except Exception:
        pass  # Cookie removal failure is non-critical


def restore_session_from_cookies(cookie_controller) -> bool:
    """
    Attempt to restore a Supabase session from browser cookies.
    If valid tokens exist, re-authenticate and populate session_state.
    Returns True if session was successfully restored.

    Handles the async timing of the cookie component:
    - 1st render after refresh: component not loaded → cookies unreadable → skip
    - 2nd render (component loaded): cookies readable → restore session → rerun
    """
    # Already authenticated in this session — skip
    if st.session_state.get("authenticated", False):
        return True

    # Already confirmed no valid cookies exist — don't keep retrying
    if st.session_state.get("_session_restore_failed", False):
        return False

    try:
        # getAll() returns None if the component hasn't loaded yet,
        # or a dict (possibly empty) once the component is ready.
        all_cookies = cookie_controller.getAll()

        if all_cookies is None:
            # Component hasn't loaded yet — DON'T set any flag.
            # Streamlit will auto-rerun when the component mounts.
            return False

        # Component is loaded — extract our tokens
        access_token = all_cookies.get(COOKIE_ACCESS_TOKEN)
        refresh_token = all_cookies.get(COOKIE_REFRESH_TOKEN)

        if not access_token or not refresh_token:
            # Component loaded but no tokens found — user genuinely not logged in
            st.session_state["_session_restore_failed"] = True
            return False

        # Try to restore session using a FRESH client (multi-user safe)
        auth_client = _create_fresh_auth_client()
        auth_response = auth_client.auth.set_session(
            access_token=access_token,
            refresh_token=refresh_token,
        )

        if auth_response and auth_response.user:
            # Fetch user profile via admin client (safe to share, no per-user state)
            admin_client = get_supabase_admin_client()
            profile_response = (
                admin_client.table("users")
                .select("*")
                .eq("id", str(auth_response.user.id))
                .single()
                .execute()
            )
            profile = profile_response.data if profile_response.data else {}

            # Populate session state
            st.session_state["authenticated"] = True
            st.session_state["user"] = auth_response.user
            st.session_state["session"] = auth_response.session
            st.session_state["profile"] = profile
            st.session_state["role"] = profile.get("role", "patient")

            # Update cookies with potentially refreshed tokens
            if auth_response.session:
                save_session_to_cookies(cookie_controller, auth_response.session)

            return True

    except Exception:
        # Tokens are expired or invalid — clear stale cookies
        st.session_state["_session_restore_failed"] = True
        try:
            clear_session_cookies(cookie_controller)
        except Exception:
            pass

    return False


# ── Auth Helper Functions ──────────────────────────────────────

def sign_up(email: str, password: str, full_name: str, role: str = "patient", phone: str = "") -> dict:
    """
    Register a new user via Supabase Auth and create their profile.
    Returns user data on success or error dict on failure.
    """
    client = get_supabase_admin_client()
    try:
        # Create auth user directly as admin to bypass rate limits and auto-confirm email
        auth_response = client.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "full_name": full_name,
                "role": role,
            }
        })

        if auth_response.user:
            # Create profile in users table
            user_data = {
                "id": str(auth_response.user.id),
                "email": email,
                "full_name": full_name,
                "phone": phone,
                "role": role,
            }
            client.table("users").insert(user_data).execute()

            return {
                "success": True,
                "user": auth_response.user,
                "message": "Account created successfully!",
            }
        else:
            return {"success": False, "message": "Sign-up failed. Please try again."}

    except Exception as e:
        error_msg = str(e)
        if "already registered" in error_msg.lower():
            return {"success": False, "message": "This email is already registered. Please sign in."}
        return {"success": False, "message": f"Sign-up error: {error_msg}"}


def sign_in(email: str, password: str) -> dict:
    """
    Sign in a user via Supabase Auth.
    Uses a FRESH client per sign-in to avoid cross-user auth leakage.
    Returns user data and session on success.
    """
    # Fresh client — auth state is isolated to this user's sign-in
    auth_client = _create_fresh_auth_client()
    try:
        auth_response = auth_client.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })

        if auth_response.user:
            # Fetch user profile via admin client (safe to share)
            admin_client = get_supabase_admin_client()
            profile = admin_client.table("users").select("*").eq("id", str(auth_response.user.id)).single().execute()

            return {
                "success": True,
                "user": auth_response.user,
                "session": auth_response.session,
                "profile": profile.data if profile.data else {},
                "message": "Signed in successfully!",
            }
        else:
            return {"success": False, "message": "Invalid credentials. Please try again."}

    except Exception as e:
        error_msg = str(e)
        if "invalid" in error_msg.lower():
            return {"success": False, "message": "Invalid email or password."}
        return {"success": False, "message": f"Sign-in error: {error_msg}"}


def sign_out(cookie_controller=None):
    """
    Sign out the current user.
    Does NOT call sign_out on the shared cached client (multi-user safe).
    Instead, just clears session state and cookies — the session tokens
    will expire naturally on Supabase's side.
    """
    # Clear session cookies from the browser
    if cookie_controller:
        clear_session_cookies(cookie_controller)

    # Clear session state (this is per-user in Streamlit)
    for key in ["user", "profile", "session", "authenticated", "role", "_session_restore_failed"]:
        if key in st.session_state:
            del st.session_state[key]


def get_current_user() -> dict:
    """Get the currently authenticated user from session state."""
    if "profile" in st.session_state and st.session_state.get("authenticated"):
        return st.session_state["profile"]
    return None


def is_authenticated() -> bool:
    """Check if a user is currently authenticated."""
    return st.session_state.get("authenticated", False)


def get_user_role() -> str:
    """Get the role of the currently authenticated user."""
    profile = get_current_user()
    if profile:
        return profile.get("role", "patient")
    return None
