"""
ERPClaw RBAC — Role-Based Access Control Utility
=================================================
Shared library for permission checking across all skills.

Functions:
- check_permission(conn, user_id, skill, action) -> bool
- require_permission(conn, user_id, skill, action) -> None (raises on deny)
- get_user_companies(conn, user_id) -> list[str]
- get_user_roles(conn, user_id, company_id=None) -> list[dict]
- resolve_telegram_user(conn, telegram_username) -> Optional[str]
- check_row_permission(conn, user_id, entity_type, entity_id) -> bool
- filter_by_permission(conn, user_id, entity_type, id_column) -> (clause, params)
- add_user_permission(conn, user_id, entity_type, entity_id, ...) -> str
- remove_user_permission(conn, user_id, entity_type, entity_id=None) -> None

Permission resolution order:
1. If no erp_user record exists for user_id → allow (RBAC not enforced yet)
2. If user has 'System Manager' role → always allow
3. Check role_permission for matching (skill, action_pattern)
4. Wildcard patterns: 'submit-*', 'list-*', '*'
5. If no matching rule found → deny

Row-level security (user_permission table):
- Restricts which specific entities (company, cost_center, warehouse, etc.)
  a user can access
- If no user_permission rows exist for a user+entity_type, access is unrestricted
- If rows exist, only matching entity_ids are allowed

Note: RBAC is opt-in. Skills call require_permission() in actions that
need enforcement. If RBAC tables are empty (no users created), all
actions are allowed to maintain backward compatibility.
"""

import fnmatch
import json


def _rbac_active(conn):
    """Check if RBAC is active (at least one erp_user exists)."""
    row = conn.execute("SELECT COUNT(*) as cnt FROM erp_user").fetchone()
    return (row["cnt"] if isinstance(row, dict) else row[0]) > 0


def resolve_telegram_user(conn, telegram_username):
    """Resolve a Telegram username to an erp_user ID.

    Returns user_id (str) or None if not found.
    """
    if not telegram_username:
        return None
    # Strip @ prefix if present
    username = telegram_username.lstrip("@")
    row = conn.execute(
        "SELECT id FROM erp_user WHERE username = ?", (username,)
    ).fetchone()
    if row:
        return row["id"] if isinstance(row, dict) else row[0]
    return None


def get_user_companies(conn, user_id):
    """Get list of company IDs a user can access.

    Returns list of company ID strings. Empty list if user has no
    company restrictions (System Manager sees all).
    """
    row = conn.execute(
        "SELECT company_ids FROM erp_user WHERE id = ?", (user_id,)
    ).fetchone()
    if not row:
        return []
    raw = row["company_ids"] if isinstance(row, dict) else row[0]
    if not raw:
        return []
    try:
        ids = json.loads(raw)
        return ids if isinstance(ids, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def get_user_roles(conn, user_id, company_id=None):
    """Get all roles assigned to a user, optionally filtered by company.

    Returns list of dicts: [{"role_id": ..., "role_name": ..., "company_id": ...}]
    """
    if company_id:
        rows = conn.execute(
            """SELECT ur.role_id, r.name AS role_name, ur.company_id
               FROM user_role ur
               JOIN role r ON r.id = ur.role_id
               WHERE ur.user_id = ?
                 AND (ur.company_id = ? OR ur.company_id IS NULL)""",
            (user_id, company_id),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT ur.role_id, r.name AS role_name, ur.company_id
               FROM user_role ur
               JOIN role r ON r.id = ur.role_id
               WHERE ur.user_id = ?""",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def _has_system_manager(conn, user_id):
    """Check if user has System Manager role (any company)."""
    row = conn.execute(
        """SELECT 1 FROM user_role ur
           JOIN role r ON r.id = ur.role_id
           WHERE ur.user_id = ? AND r.name = 'System Manager'
           LIMIT 1""",
        (user_id,),
    ).fetchone()
    return row is not None


def _match_action_pattern(pattern, action):
    """Match an action against a pattern using fnmatch-style wildcards.

    Examples:
        '*'         matches everything
        'list-*'    matches list-accounts, list-invoices, etc.
        'submit-*'  matches submit-journal-entry, submit-payment, etc.
        'add-*'     matches add-customer, add-item, etc.
    """
    return fnmatch.fnmatch(action, pattern)


def check_permission(conn, user_id, skill, action):
    """Check if a user has permission to perform an action.

    Args:
        conn: SQLite connection
        user_id: erp_user.id (not telegram username)
        skill: skill name (e.g. 'erpclaw-gl')
        action: action name (e.g. 'submit-journal-entry')

    Returns:
        True if allowed, False if denied.
        Returns True if RBAC is not active (no users created).
    """
    if not _rbac_active(conn):
        return True

    if not user_id:
        return True  # No user context → allow (backward compat)

    # System Manager bypasses all checks
    if _has_system_manager(conn, user_id):
        return True

    # Get all role IDs for this user
    role_rows = conn.execute(
        "SELECT DISTINCT role_id FROM user_role WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    if not role_rows:
        return False  # User exists but has no roles → deny

    role_ids = [r["role_id"] if isinstance(r, dict) else r[0] for r in role_rows]

    # Check permissions for each role
    placeholders = ",".join("?" for _ in role_ids)
    perms = conn.execute(
        f"""SELECT skill, action_pattern, allowed
            FROM role_permission
            WHERE role_id IN ({placeholders})""",
        role_ids,
    ).fetchall()

    # Find matching permission rules (most specific first)
    for perm in perms:
        p_skill = perm["skill"] if isinstance(perm, dict) else perm[0]
        p_pattern = perm["action_pattern"] if isinstance(perm, dict) else perm[1]
        p_allowed = perm["allowed"] if isinstance(perm, dict) else perm[2]

        # Skill must match exactly or be wildcard
        if p_skill != skill and p_skill != "*":
            continue

        # Action must match the pattern
        if _match_action_pattern(p_pattern, action):
            return bool(p_allowed)

    return False  # No matching rule → deny


def require_permission(conn, user_id, skill, action):
    """Require permission or raise an error.

    Raises dict-like error suitable for JSON output if denied.
    """
    if not check_permission(conn, user_id, skill, action):
        raise PermissionError(
            f"Permission denied: user cannot perform '{action}' on '{skill}'"
        )


def resolve_telegram_user_id(conn, telegram_user_id):
    """Resolve a Telegram numeric user ID to an erp_user ID.

    Returns user_id (str) or None if not linked.
    """
    if not telegram_user_id:
        return None
    row = conn.execute(
        "SELECT id FROM erp_user WHERE telegram_user_id = ? AND status = 'active'",
        (str(telegram_user_id),),
    ).fetchone()
    if row:
        return row["id"] if isinstance(row, dict) else row[0]
    return None


def enforce_telegram_rbac(conn, telegram_user_id, skill, action):
    """Enforce RBAC for a Telegram user. No-op if telegram_user_id is None.

    Resolves telegram_user_id → erp_user.id, then checks permission.
    Raises PermissionError if the user is not linked or not authorized.

    Args:
        conn: SQLite connection
        telegram_user_id: Telegram numeric user ID (str or int)
        skill: skill name (e.g. 'erpclaw-journals')
        action: action name (e.g. 'submit-journal-entry')
    """
    if not telegram_user_id:
        return  # No-op — backward compatible

    if not _rbac_active(conn):
        return  # RBAC not active — allow all

    user_id = resolve_telegram_user_id(conn, telegram_user_id)
    if not user_id:
        raise PermissionError(
            f"Telegram user {telegram_user_id} is not linked to any ERP user"
        )

    require_permission(conn, user_id, skill, action)


# ---------------------------------------------------------------------------
# Row-level security (user_permission table)
# ---------------------------------------------------------------------------


def check_row_permission(conn, user_id, entity_type, entity_id):
    """Check if a user has permission to access a specific entity row.

    Returns True if:
    - RBAC is not active
    - User is System Manager
    - No user_permission rows exist for this user+entity_type (unrestricted)
    - A matching user_permission row exists for this user+entity_type+entity_id
    """
    if not _rbac_active(conn):
        return True
    if _has_system_manager(conn, user_id):
        return True

    # Check if any restrictions exist for this user + entity_type
    restrictions = conn.execute(
        "SELECT id FROM user_permission WHERE user_id = ? AND entity_type = ?",
        (user_id, entity_type)
    ).fetchone()

    if not restrictions:
        return True  # No restrictions defined = unrestricted access

    # Check for specific entity permission
    allowed = conn.execute(
        "SELECT id FROM user_permission WHERE user_id = ? AND entity_type = ? AND entity_id = ?",
        (user_id, entity_type, entity_id)
    ).fetchone()

    return allowed is not None


def filter_by_permission(conn, user_id, entity_type, id_column="id"):
    """Return a WHERE clause fragment and params for row-level filtering.

    Returns (where_clause, params) tuple.
    - If RBAC not active or user is System Manager: ("1=1", [])
    - If no restrictions for user+entity_type: ("1=1", [])
    - If restrictions exist: ("{id_column} IN (SELECT entity_id FROM user_permission WHERE ...)", [user_id, entity_type])
    """
    if not _rbac_active(conn):
        return "1=1", []
    if _has_system_manager(conn, user_id):
        return "1=1", []

    # Check if any restrictions exist
    restrictions = conn.execute(
        "SELECT id FROM user_permission WHERE user_id = ? AND entity_type = ?",
        (user_id, entity_type)
    ).fetchone()

    if not restrictions:
        return "1=1", []  # No restrictions = see everything

    clause = f"{id_column} IN (SELECT entity_id FROM user_permission WHERE user_id = ? AND entity_type = ?)"
    return clause, [user_id, entity_type]


def add_user_permission(conn, user_id, entity_type, entity_id,
                        can_read=True, can_write=False,
                        can_submit=False, can_cancel=False):
    """Add a row-level permission for a user.

    Args:
        user_id: the user to grant permission to
        entity_type: the entity type being restricted (e.g. 'company', 'warehouse')
        entity_id: the specific entity ID to allow
        can_read: allow read access (default True)
        can_write: allow write access (default False)
        can_submit: allow submit access (default False)
        can_cancel: allow cancel access (default False)
    """
    import uuid
    perm_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO user_permission
           (id, user_id, entity_type, entity_id, can_read, can_write, can_submit, can_cancel)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (perm_id, user_id, entity_type, entity_id,
         1 if can_read else 0, 1 if can_write else 0,
         1 if can_submit else 0, 1 if can_cancel else 0)
    )
    return perm_id


def remove_user_permission(conn, user_id, entity_type, entity_id=None):
    """Remove row-level permission(s) for a user.

    If entity_id is None, removes ALL permissions for user+entity_type.
    """
    if entity_id:
        conn.execute(
            "DELETE FROM user_permission WHERE user_id = ? AND entity_type = ? AND entity_id = ?",
            (user_id, entity_type, entity_id)
        )
    else:
        conn.execute(
            "DELETE FROM user_permission WHERE user_id = ? AND entity_type = ?",
            (user_id, entity_type)
        )


# ---------------------------------------------------------------------------
# Default permission matrix for seeding role_permission table
# ---------------------------------------------------------------------------

ROLE_PERMISSIONS = {
    "System Manager": [("*", "*")],
    "Accounts Manager": [
        ("erpclaw-gl", "*"),
        ("erpclaw-journals", "*"),
        ("erpclaw-payments", "*"),
        ("erpclaw-tax", "*"),
        ("erpclaw-reports", "*"),
        ("erpclaw-analytics", "list-*"),
        ("erpclaw-analytics", "get-*"),
        ("erpclaw-analytics", "*-ratios"),
        ("erpclaw-analytics", "*-dashboard"),
    ],
    "Accounts User": [
        ("erpclaw-gl", "list-*"),
        ("erpclaw-gl", "get-*"),
        ("erpclaw-journals", "add-*"),
        ("erpclaw-journals", "list-*"),
        ("erpclaw-journals", "get-*"),
        ("erpclaw-journals", "submit-*"),
        ("erpclaw-payments", "add-*"),
        ("erpclaw-payments", "list-*"),
        ("erpclaw-payments", "get-*"),
        ("erpclaw-payments", "submit-*"),
        ("erpclaw-tax", "list-*"),
        ("erpclaw-tax", "get-*"),
        ("erpclaw-reports", "*"),
        ("erpclaw-analytics", "list-*"),
        ("erpclaw-analytics", "get-*"),
    ],
    "Stock Manager": [
        ("erpclaw-inventory", "*"),
        ("erpclaw-selling", "*"),
        ("erpclaw-buying", "*"),
        ("erpclaw-manufacturing", "*"),
    ],
    "Stock User": [
        ("erpclaw-inventory", "list-*"),
        ("erpclaw-inventory", "get-*"),
        ("erpclaw-inventory", "add-stock-entry"),
        ("erpclaw-inventory", "submit-stock-entry"),
        ("erpclaw-selling", "list-*"),
        ("erpclaw-selling", "get-*"),
        ("erpclaw-buying", "list-*"),
        ("erpclaw-buying", "get-*"),
    ],
    "HR Manager": [
        ("erpclaw-hr", "*"),
        ("erpclaw-payroll", "*"),
    ],
    "HR User": [
        ("erpclaw-hr", "list-*"),
        ("erpclaw-hr", "get-*"),
        ("erpclaw-hr", "add-leave-application"),
        ("erpclaw-hr", "mark-attendance"),
        ("erpclaw-hr", "add-expense-claim"),
        ("erpclaw-payroll", "list-*"),
        ("erpclaw-payroll", "get-*"),
    ],
    "Sales Manager": [
        ("erpclaw-crm", "*"),
        ("erpclaw-selling", "*"),
    ],
    "Sales User": [
        ("erpclaw-crm", "list-*"),
        ("erpclaw-crm", "get-*"),
        ("erpclaw-crm", "add-*"),
        ("erpclaw-crm", "update-*"),
        ("erpclaw-selling", "list-*"),
        ("erpclaw-selling", "get-*"),
        ("erpclaw-selling", "add-*"),
    ],
    "Purchase Manager": [
        ("erpclaw-buying", "*"),
    ],
    "Purchase User": [
        ("erpclaw-buying", "list-*"),
        ("erpclaw-buying", "get-*"),
        ("erpclaw-buying", "add-*"),
    ],
    "Analytics User": [
        ("erpclaw-reports", "*"),
        ("erpclaw-analytics", "*"),
        ("erpclaw-ai-engine", "list-*"),
        ("erpclaw-ai-engine", "get-*"),
    ],
}


def register_role(role_name: str, default_permissions: list[tuple[str, str]]):
    """Register a vertical-specific role with default permissions.

    Verticals call this during init to add their roles to the
    permission matrix without modifying shared lib source.

    Args:
        role_name: e.g. 'Site Foreman', 'Attorney'
        default_permissions: List of (skill, action_pattern) tuples.
            e.g. [('buildclaw', '*'), ('erpclaw-projects', 'list-*')]
    """
    ROLE_PERMISSIONS[role_name] = default_permissions


def seed_role_permissions(conn):
    """Seed role_permission table with default permissions.

    Call this after roles are created (init_db seeds roles).
    Idempotent — uses INSERT OR IGNORE.
    """
    import uuid

    for role_name, permissions in ROLE_PERMISSIONS.items():
        role_row = conn.execute(
            "SELECT id FROM role WHERE name = ?", (role_name,)
        ).fetchone()
        if not role_row:
            continue
        role_id = role_row["id"] if isinstance(role_row, dict) else role_row[0]

        for skill, pattern in permissions:
            conn.execute(
                """INSERT OR IGNORE INTO role_permission
                   (id, role_id, skill, action_pattern, allowed)
                   VALUES (?, ?, ?, ?, 1)""",
                (str(uuid.uuid4()), role_id, skill, pattern),
            )
    conn.commit()
