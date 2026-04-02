import os
import json
from contextlib import contextmanager
from mysql.connector import connect, Error
from .router_core import MCPRouter
from dotenv import load_dotenv
 
load_dotenv()
 
# ── Config ────────────────────────────────────────────────────────────────
 
_DB = dict(
    host     = os.getenv("GLPI_DB_HOST",     "10.10.10.181"),
    user     = os.getenv("GLPI_DB_USER",     "wajeepradit.p"),
    password = os.getenv("GLPI_DB_PASSWORD", "Az_123456"),
    database = os.getenv("GLPI_DB_NAME",     "glpi"),
    port     = int(os.getenv("GLPI_DB_PORT", 3306)),
    connection_timeout = 5,
    use_pure = True,
)
 
router = MCPRouter("GLPI")
 
# ── DB helper ─────────────────────────────────────────────────────────────
 
@contextmanager
def _db():
    """Context manager: open → yield cursor → close (always)."""
    conn = connect(**_DB)
    cur  = conn.cursor(dictionary=True)
    try:
        yield cur
    finally:
        cur.close()
        conn.close()
 
def _json(rows: list) -> str:
    return json.dumps(rows, default=str, ensure_ascii=False)
 
# ── Column map ────────────────────────────────────────────────────────────
 
_COLS = {
    # identity
    "id":                    "c.id",
    "computer_name":         "c.name",
    "serial":                "c.serial",
    "otherserial":           "c.otherserial",
    "uuid":                  "c.uuid",
    # org
    "entity_name":           "e.completename",
    "location_name":         "l.completename",
    # people
    "user_name":             "u.name",
    "group_name":            "g.name",
    "contact":               "c.contact",
    # hardware
    "manufacturer_name":     "m.name",
    "model_name":            "cm.name",
    "type_name":             "ct.name",
    "status_name":           "s.name",
    # time
    "last_inventory_update": "c.last_inventory_update",
    "last_boot":             "c.last_boot",
    "date_creation":         "c.date_creation",
    # wifi
    "wifi_mac":              "wifi.mac",
    "wifi_ip":               "wifi.ip_address",
    # misc
    "comment":               "c.comment",
    "is_dynamic":            "c.is_dynamic",
}
 
_PRESETS = {
    "min":      ["id", "computer_name", "wifi_ip"],
    "identity": ["id", "computer_name", "serial", "manufacturer_name", "model_name", "type_name"],
    "network":  ["id", "computer_name", "wifi_mac", "wifi_ip"],
    "people":   ["id", "computer_name", "user_name", "group_name", "contact", "location_name"],
    "status":   ["id", "computer_name", "status_name", "last_inventory_update", "last_boot", "is_dynamic"],
    "full":     list(_COLS.keys()),
}
 
_WIFI_COLS = {"wifi_mac", "wifi_ip"}
 
_JOINS = """
FROM glpi_computers c
LEFT JOIN glpi_entities       e   ON c.entities_id         = e.id
LEFT JOIN glpi_locations      l   ON c.locations_id        = l.id
LEFT JOIN glpi_computermodels cm  ON c.computermodels_id   = cm.id
LEFT JOIN glpi_computertypes  ct  ON c.computertypes_id    = ct.id
LEFT JOIN glpi_manufacturers  m   ON c.manufacturers_id    = m.id
LEFT JOIN glpi_users          u   ON c.users_id            = u.id
LEFT JOIN glpi_groups         g   ON c.groups_id           = g.id
LEFT JOIN glpi_states         s   ON c.states_id           = s.id"""
 
_WIFI_JOIN = """
LEFT JOIN (
    SELECT np.items_id AS computer_id, MIN(np.mac) AS mac, MIN(ip.name) AS ip_address
    FROM glpi_networkports np
    JOIN glpi_networknames  nn ON nn.items_id = np.id AND nn.itemtype = 'NetworkPort' AND nn.is_deleted = 0
    JOIN glpi_ipaddresses   ip ON ip.items_id = nn.id AND ip.itemtype = 'NetworkName'
                               AND ip.is_deleted = 0 AND ip.name NOT LIKE '%:%'
    WHERE np.itemtype = 'Computer' AND np.is_deleted = 0
      AND (np.name LIKE '%wlan%' OR np.name LIKE '%wifi%' OR np.name LIKE '%wireless%'
           OR np.instantiation_type = 'NetworkPortWifi')
    GROUP BY np.items_id
) wifi ON wifi.computer_id = c.id"""
 
def _build_where(extra: str) -> str:
    base = "WHERE c.is_deleted = 0"
    return f"{base} AND ({extra.strip()})" if extra.strip() else base
 
def _resolve_cols(columns: str) -> list[str] | str:
    names = _PRESETS.get(columns.strip()) or [c.strip() for c in columns.split(",") if c.strip()]
    bad = [c for c in names if c not in _COLS]
    if bad:
        return f"Unknown columns: {bad}. Available: {sorted(_COLS)}"
    return names
 
# ── Tools ─────────────────────────────────────────────────────────────────
 
@router.tool()
def count_computers(where: str = "") -> str:
    """Count computers (no data fetch). Use before get_computers to gauge result size.
 
    Args:
        where: SQL condition without WHERE keyword. e.g. "s.name = 'Assigned'"
    """
    try:
        with _db() as cur:
            cur.execute(f"SELECT COUNT(*) AS n {_JOINS} {_build_where(where)}")
            return str(cur.fetchone()["n"])
    except Error as e:
        return f"SQL Error: {e}"
 
 
@router.tool()
def get_computers(
    columns:  str = "min",
    where:    str = "",
    order_by: str = "",
    limit:    int = 100,
) -> str:
    """Query GLPI computers. Returns compact JSON.
 
    Args:
        columns:  Preset name OR comma-separated column names.
                  Presets : min | identity | network | people | status | full
                  Columns : id, computer_name, serial, otherserial, uuid,
                            entity_name, location_name,
                            user_name, group_name, contact,
                            manufacturer_name, model_name, type_name, status_name,
                            last_inventory_update, last_boot, date_creation,
                            wifi_mac, wifi_ip, comment, is_dynamic
        where:    SQL condition. e.g. "c.name = 'PC001'" | "u.name LIKE '%john%'"
        order_by: e.g. "c.name ASC" | "c.last_boot DESC"
        limit:    1–2000 (default 100)
    """
    col_names = _resolve_cols(columns)
    if isinstance(col_names, str):   # error message
        return col_names
 
    select = ", ".join(f"{_COLS[c]} AS {c}" for c in col_names)
    wifi   = _WIFI_JOIN if (any(c in _WIFI_COLS for c in col_names) or "wifi." in where) else ""
    order  = f"ORDER BY {order_by.strip()}" if order_by.strip() else ""
    limit  = max(1, min(limit, 2000))
 
    sql = f"SELECT {select} {_JOINS} {wifi} {_build_where(where)} {order} LIMIT {limit}"
 
    try:
        with _db() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            return "[]" if not rows else _json(rows)
    except Error as e:
        return f"SQL Error: {e}"
 
 
@router.tool()
def run_query(query: str) -> str:
    """Run any SELECT query for custom/advanced lookups not covered by get_computers.
 
    Args:
        query: A SELECT SQL statement.
    """
    if not query.strip().upper().startswith("SELECT"):
        return "Only SELECT queries are allowed."
    try:
        with _db() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            return "[]" if not rows else _json(rows)
    except Error as e:
        return f"SQL Error: {e}"
 