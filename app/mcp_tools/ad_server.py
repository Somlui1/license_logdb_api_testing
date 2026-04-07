"""
AD MCP Server — ADInfo Equivalent (Read-Only)
==============================================
ครอบคลุม object type เดียวกับ Cjwdev ADInfo:
  Users · Computers · Contacts · Groups · OUs/Containers · GPOs

Pattern: Scope-then-Filter
  1. ดึงข้อมูลจาก AD ด้วย LDAP scope กว้างๆ (objectClass + search_base)
  2. Filter ที่ server-side ด้วย Python — รองรับ contains / startswith /
     endswith / boolean / days / member_of / regex
  3. คืนเฉพาะ fields ที่ client ระบุ → ประหยัด token สูงสุด

หมายเหตุ: READ-ONLY ทั้งหมด ไม่มี write/modify operation ใดๆ
"""

from __future__ import annotations

import json
import os
import re
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from typing import Any

from ldap3 import (
    Server, Connection, ALL, SUBTREE, NTLM,
    ALL_ATTRIBUTES,
)
from ldap3.core.exceptions import LDAPException
from dotenv import load_dotenv

from .router_core import MCPRouter   # ← ปรับ import ตาม project structure จริง
import time
import concurrent.futures
from functools import lru_cache

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────

# ── Config ─────────────────────────────────────────────────────────────────────

_AD_HOSTS    = [h.strip() for h in os.getenv("AD_HOSTS", os.getenv("AD_HOST", "10.10.10.250")).split(",")]
_AD_USER     = os.getenv("AD_USER",     "svc_mcp_readonly@aapico.com")
_AD_PASSWORD = os.getenv("AD_PASSWORD", "")
_AD_BASE_DN  = os.getenv("AD_BASE_DN",  "DC=aapico,DC=com")

# ── กำหนดค่า OU Mapping (AAPICO Group Structure) ───────────────────────────────
_OU_MAP = {
    # ── Root / Defaults ──
    "all":               _AD_BASE_DN,
    "all_users":         f"CN=Users,{_AD_BASE_DN}",
    "all_computers":     f"CN=Computers,{_AD_BASE_DN}",
    
    # ── Companies / Business Units (Top-Level OUs) ──
    "aa":                f"OU=AA,{_AD_BASE_DN}",
    "ac":                f"OU=AC,{_AD_BASE_DN}",
    "aerp":              f"OU=AERP,{_AD_BASE_DN}",
    "af":                f"OU=AF,{_AD_BASE_DN}",
    "ah":                f"OU=AH,{_AD_BASE_DN}",
    "aha":               f"OU=AHA,{_AD_BASE_DN}",
    "ahp":               f"OU=AHP,{_AD_BASE_DN}",
    "ahr":               f"OU=AHR,{_AD_BASE_DN}",
    "aht":               f"OU=AHT,{_AD_BASE_DN}",
    "aits":              f"OU=AITS,{_AD_BASE_DN}",
    "al":                f"OU=AL,{_AD_BASE_DN}",
    "ap":                f"OU=AP,{_AD_BASE_DN}",
    "apr":               f"OU=APR,{_AD_BASE_DN}",
    "as_group":          f"OU=AS,{_AD_BASE_DN}",  # ใช้ as_group ป้องกันคำสงวน
    "asp":               f"OU=ASP,{_AD_BASE_DN}",
    
    # ── Shared Services / Functional OUs ──
    "contacts":          f"OU=Contact,{_AD_BASE_DN}",
    "managed_desktop":   f"OU=Managed Desktop,{_AD_BASE_DN}",
    "managed_groups":    f"OU=Managed Groups,{_AD_BASE_DN}",
    "showroom":          f"OU=Showroom,{_AD_BASE_DN}",
    "domain_controllers":f"OU=Domain Controllers,{_AD_BASE_DN}",
    "user_delete":       f"OU=User Delete,{_AD_BASE_DN}",
}

# ── Cache ──────────────────────────────────────────────────────────────────────
_fetch_cache: dict[str, tuple[float, list[dict]]] = {}
_CACHE_TTL = 300  # 5 minutes

# ── Cache และ Helper สำหรับ Domain Policy ───────────────────────────────────
_DOMAIN_MAX_PWD_AGE_DAYS = None

def _get_max_pwd_age() -> int:
    global _DOMAIN_MAX_PWD_AGE_DAYS
    if _DOMAIN_MAX_PWD_AGE_DAYS is not None:
        return _DOMAIN_MAX_PWD_AGE_DAYS
    try:
        conn = _connect()
        conn.search(_AD_BASE_DN, "(objectClass=*)", attributes=["maxPwdAge"])
        if conn.entries and conn.entries[0].maxPwdAge.value:
            val = abs(int(conn.entries[0].maxPwdAge.value)) // 10000000 // 60
            _DOMAIN_MAX_PWD_AGE_DAYS = val // 1440
        else:
            _DOMAIN_MAX_PWD_AGE_DAYS = 0
        conn.unbind()
    except Exception:
        _DOMAIN_MAX_PWD_AGE_DAYS = 0
    return _DOMAIN_MAX_PWD_AGE_DAYS

router = MCPRouter("AD")

# ── LDAP attribute maps ────────────────────────────────────────────────────────
# (LDAP attr → friendly key ที่ client เห็น)

_USER_LDAP = {
    "sAMAccountName":    "username",
    "displayName":       "display_name",
    "givenName":         "first_name",
    "sn":                "last_name",
    "mail":              "email",
    "telephoneNumber":   "phone",
    "mobile":            "mobile",
    "department":        "department",
    "title":             "job_title",
    "company":           "company",
    "manager":           "manager",
    "employeeID":        "employee_id",
    "userAccountControl":"_uac",
    "lockoutTime":       "_lockout_time",
    "lastLogonTimestamp":"last_logon",
    "pwdLastSet":        "password_last_set",
    "whenCreated":       "creation_date",
    "whenChanged":       "modification_date",
    "distinguishedName": "distinguished_name",
    "objectGUID":        "guid",
    "userPrincipalName": "upn",
    "msExchHideFromAddressLists": "hidden_from_gal",
    "accountExpires":    "account_expires",
    "thumbnailPhoto":    "_has_photo",
    "proxyAddresses":    "smtp_addresses",
    "homePhone":         "home_phone",
    "st":                "state",
    "postalCode":        "postal_code",
    "employeeNumber":    "employee_number",
    "profilePath":       "profile_path",
    "scriptPath":        "logon_script",
    "homeDirectory":     "home_directory",
    "homeDrive":         "home_drive",
    "info":              "notes",
    "badPwdCount":       "bad_password_count",
    "logonCount":        "logon_count",
    "objectSid":         "sid",
}

_COMPUTER_LDAP = {
    "cn":                        "name",
    "dNSHostName":               "dns_hostname",
    "operatingSystem":           "operating_system",
    "operatingSystemVersion":    "os_version",
    "operatingSystemServicePack":"service_pack",
    "description":               "description",
    "managedBy":                 "managed_by",
    "userAccountControl":        "_uac",
    "pwdLastSet":                "password_last_changed",
    "lastLogonTimestamp":        "last_logon",
    "whenCreated":               "creation_date",
    "whenChanged":               "modification_date",
    "distinguishedName":         "distinguished_name",
    "objectGUID":                "guid",
    "objectSid":                 "sid",
}

_CONTACT_LDAP = {
    "cn":                "name",
    "displayName":       "display_name",
    "givenName":         "first_name",
    "sn":                "last_name",
    "mail":              "email",
    "telephoneNumber":   "phone",
    "mobile":            "mobile",
    "facsimileTelephoneNumber": "fax",
    "company":           "company",
    "department":        "department",
    "title":             "job_title",
    "streetAddress":     "street",
    "l":                 "city",
    "co":                "country",
    "wWWHomePage":       "web_page",
    "physicalDeliveryOfficeName": "office",
    "description":       "description",
    "memberOf":          "group_membership_direct",
    "whenCreated":       "creation_date",
    "whenChanged":       "modification_date",
    "distinguishedName": "distinguished_name",
    "objectGUID":        "guid",
}

_GROUP_LDAP = {
    "cn":                "name",
    "description":       "description",
    "groupType":         "_group_type_raw",
    "member":            "members_direct",
    "managedBy":         "managed_by",
    "mail":              "email",
    "whenCreated":       "creation_date",
    "whenChanged":       "modification_date",
    "distinguishedName": "distinguished_name",
    "objectGUID":        "guid",
    "objectSid":         "sid",
    "info":              "notes",
}

_OU_LDAP = {
    "ou":                "name",
    "description":       "description",
    "distinguishedName": "distinguished_name",
    "whenCreated":       "creation_date",
    "whenChanged":       "modification_date",
    "objectGUID":        "guid",
    "gPLink":            "_gplink_raw",   # computed → linked_gpos
}

# ── Reverse Mappings (Friendly → LDAP) ──────────────────────────────────────────
# สำหรับใช้สร้าง LDAP Filter จาก where clause (Push-down)
_USER_LDAP_REV     = {v: k for k, v in _USER_LDAP.items()}
_COMPUTER_LDAP_REV = {v: k for k, v in _COMPUTER_LDAP.items()}
_CONTACT_LDAP_REV  = {v: k for k, v in _CONTACT_LDAP.items()}
_GROUP_LDAP_REV    = {v: k for k, v in _GROUP_LDAP.items()}
_OU_LDAP_REV       = {v: k for k, v in _OU_LDAP.items()}

# เพิ่ม Alias ทั่วไปที่ AI มักส่งมา (LDAP names → Friendly names)
_ALIAS_MAP = {
    "sAMAccountName": "username",
    "displayName":    "display_name",
    "givenName":      "first_name",
    "sn":             "last_name",
    "mail":           "email",
    "title":          "job_title",
    "company":        "company",
    "department":     "department"
}

# Presets (ชื่อ friendly → list of friendly keys)
_USER_PRESETS = {
    "min":         ["username", "display_name", "email"],
    "identity":    ["username", "display_name", "first_name", "last_name",
                    "email", "department", "job_title", "company"],
    "contact_info":["username", "display_name", "email", "phone", "mobile",
                    "department", "job_title"],
    "address":     ["username", "display_name", "street", "city", "state",
                    "postal_code", "country"],
    "account":     ["username", "display_name", "upn", "disabled",
                    "account_locked", "last_logon", "password_last_set",
                    "bad_password_count", "logon_count", "account_expires"],
    "exchange":    ["username", "display_name", "email", "smtp_addresses",
                    "hidden_from_gal", "has_photo"],
    "groups":      ["username", "display_name", "group_membership_direct"],
    "full":        None,  # None = ทุก field
}

_COMPUTER_PRESETS = {
    "min":      ["name", "dns_hostname", "operating_system"],
    "identity": ["name", "dns_hostname", "operating_system", "os_version",
                 "service_pack", "managed_by"],
    "status":   ["name", "dns_hostname", "disabled", "last_logon",
                 "password_last_changed", "creation_date"],
    "groups":   ["name", "dns_hostname", "group_membership_direct"],
    "full":     None,
}

_CONTACT_PRESETS = {
    "min":  ["name", "display_name", "email", "phone"],
    "full": None,
}

_GROUP_PRESETS = {
    "min":     ["name", "description", "group_type", "group_scope"],
    "members": ["name", "description", "members_direct",
                "member_count", "group_type", "group_scope"],
    "full":    None,
}

_OU_PRESETS = {
    "min":  ["name", "distinguished_name", "description"],
    "full": None,
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def _json(data: Any) -> str:
    return json.dumps(data, default=str, ensure_ascii=False)

def _wrap(rows: list, limit: int, total_before_limit: int, offset: int = 0) -> str:
    """คืนผลลัพธ์แบบมี metadata ครอบ"""
    return _json({
        "count": len(rows),
        "total_matched": total_before_limit,
        "offset": offset,
        "limit": limit,
        "truncated": total_before_limit > (offset + len(rows)),
        "data": rows,
    })

def _resolve_ou(ou_key: str) -> tuple[str, str | None]:
    key = ou_key.strip().lower()
    if key in _OU_MAP:
        return _OU_MAP[key], None
    if "dc=" in ou_key.lower():
        return ou_key.strip(), None
    return "", f"Unknown ou_key '{ou_key}'. ดู list_ou_structure() สำหรับ key ที่ใช้ได้"

def _filetime_to_dt(ft: Any) -> datetime | None:
    if ft is None or ft == 0 or ft == 9223372036854775807:
        return None
    if isinstance(ft, datetime):
        return ft.replace(tzinfo=timezone.utc) if ft.tzinfo is None else ft
    if isinstance(ft, int):
        epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
        return epoch + timedelta(microseconds=ft // 10)
    return None

def _days_ago(dt: datetime | None) -> int | None:
    if not dt:
        return None
    now = datetime.now(timezone.utc)
    dt  = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    return (now - dt).days

def _uac_disabled(uac: Any) -> bool:
    try:
        return bool(int(uac or 0) & 0x0002)
    except (ValueError, TypeError):
        return False

def _uac_locked(lockout: Any) -> bool:
    if not lockout:
        return False
    # ถ้าเป็น datetime แสดงว่ามีค่า lockoutTime อยู่จริง (ไม่ใช่ 0)
    if isinstance(lockout, datetime):
        return True
    try:
        return int(lockout) != 0
    except (ValueError, TypeError):
        return False

def _uac_pwd_never_expires(uac: Any) -> bool:
    try:
        return bool(int(uac or 0) & 0x10000)
    except (ValueError, TypeError):
        return False

def _parse_dn_cn(dn: str | None) -> str | None:
    if not dn:
        return None
    m = re.search(r"CN=([^,]+)", str(dn), re.IGNORECASE)
    return m.group(1) if m else dn

def _group_type(raw: Any) -> tuple[str, str]:
    """แปลง groupType integer → (type, scope)"""
    v = int(raw or 0)
    gtype  = "Security" if v & 0x80000000 else "Distribution"
    if   v & 0x00000001: scope = "System"
    elif v & 0x00000002: scope = "Global"
    elif v & 0x00000004: scope = "Domain Local"
    elif v & 0x00000008: scope = "Universal"
    else:                scope = "Unknown"
    return gtype, scope

def _parse_gplink(raw: str | None) -> list[str]:
    if not raw:
        return []
    return re.findall(r"CN=([^,\]]+)", raw)

def _attr(entry_dict: dict, ldap_key: str) -> Any:
    val = entry_dict.get(ldap_key, [None])
    if isinstance(val, list):
        return val[0] if len(val) == 1 else (val if val else None)
    return val

def _attr_list(entry_dict: dict, ldap_key: str) -> list:
    val = entry_dict.get(ldap_key, [])
    return val if isinstance(val, list) else [val]

# ── Connection ─────────────────────────────────────────────────────────────────

from ldap3 import ServerPool, FIRST

def _connect(host: str | None = None) -> Connection:
    # เตรียมรายชื่อเซิร์ฟเวอร์ที่ต้องการลอง (ถ้าระบุ host เจาะจงให้ลองแค่ตัวนั้น)
    targets = [host] if host else _AD_HOSTS
    
    # สร้าง Server objects สำหรับทั้ง LDAP (389) และ LDAPS (636)
    server_list = []
    for t in targets:
        # ลองทั้งแบบธรรมดาและ SSL (ลด timeout และเอา get_info=ALL ออกเพื่อความเร็ว)
        server_list.append(Server(t, use_ssl=False, get_info=None, connect_timeout=2))
        server_list.append(Server(t, use_ssl=True,  get_info=None, connect_timeout=2))
    
    # ใช้ ServerPool เพื่อให้ ldap3 จัดการเรื่อง Failover/Retry ให้อัตโนมัติ
    pool = ServerPool(server_list, pool_strategy=FIRST, active=True, exhaust=True)
    
    try:
        conn = Connection(
            pool,
            user=_AD_USER,
            password=_AD_PASSWORD,
            authentication=NTLM,
            auto_bind=True,
            read_only=True,
        )
        return conn
    except Exception as e:
        # ถ้าเชื่อมต่อไม่ได้เลยหลังจากลองทุกตัวใน Pool
        raise Exception(f"LDAP Connection Failed after trying all hosts/ports: {str(e)}")

def _query_single_dc(host: str, dn: str) -> int:
    """Helper for parallel DC query."""
    try:
        conn = _connect(host)
        conn.search(dn, "(objectClass=*)", attributes=["lastLogon"])
        if conn.entries:
            val = conn.entries[0].lastLogon.value
            conn.unbind()
            return int(val or 0)
        conn.unbind()
    except Exception:
        pass
    return 0

def _get_latest_last_logon(dn: str) -> datetime | None:
    """Query lastLogon from all DCs in parallel and return the most recent one."""
    if not _AD_HOSTS:
        return None
    if len(_AD_HOSTS) == 1:
        # ถ้ามี DC เดียว ไม่ต้องใช้ thread pool
        ft = _query_single_dc(_AD_HOSTS[0], dn)
        return _filetime_to_dt(ft) if ft > 0 else None

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(_AD_HOSTS)) as executor:
        futures = {executor.submit(_query_single_dc, host, dn): host for host in _AD_HOSTS}
        results = []
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    
    latest_ft = max(results) if results else 0
    return _filetime_to_dt(latest_ft) if latest_ft > 0 else None

# ── Coarse fetchers ────────────────────────────────────────────────────────────

def _fetch(search_base: str, ldap_filter: str, attrs: list[str], limit: int = 5000, use_cache: bool = True) -> list[dict]:
    """Fetch objects using Paged Search with TTL Cache."""
    cache_key = f"{search_base}|{ldap_filter}|{','.join(sorted(attrs))}"
    
    if use_cache:
        cached = _fetch_cache.get(cache_key)
        if cached:
            ts, data = cached
            if time.time() - ts < _CACHE_TTL:
                return data

    conn = _connect()
    results = []
    
    try:
        entries = conn.extend.standard.paged_search(
            search_base=search_base,
            search_filter=ldap_filter,
            search_scope=SUBTREE,
            attributes=attrs,
            paged_size=1000,
            generator=True
        )

        for entry in entries:
            if 'attributes' in entry:
                results.append(entry['attributes'])
            if len(results) >= limit:
                break
    finally:
        conn.unbind()
    
    if use_cache:
        _fetch_cache[cache_key] = (time.time(), results)
        
    return results

def _fetch_count(search_base: str, ldap_filter: str, limit: int = 100000) -> int:
    """Efficiently count objects without storing them in memory."""
    conn = _connect()
    count = 0
    try:
        # Request no attributes for maximum speed
        entries = conn.extend.standard.paged_search(
            search_base=search_base,
            search_filter=ldap_filter,
            search_scope=SUBTREE,
            attributes=[],
            paged_size=1000,
            generator=True
        )
        for entry in entries:
            if 'attributes' in entry:
                count += 1
            if count >= limit:
                break
    finally:
        conn.unbind()
    return count


def _build_users(search_base: str, member_of_dn: str | None = None, attrs: list[str] | None = None, where_f: dict | None = None, extra_ldap_filter: str | None = None) -> list[dict]:
    ldap_filter = "(&(objectClass=user)(objectCategory=person))"
    if member_of_dn:
        ldap_filter = f"(&(objectClass=user)(objectCategory=person)(memberOf:1.2.840.113556.1.4.1941:={member_of_dn}))"
    
    # Push-down basic filters to LDAP
    if where_f:
        pushed = _build_pushed_ldap_filter(where_f, _USER_LDAP_REV)
        if pushed:
            ldap_filter = f"(&{ldap_filter}{pushed})"
    
    if extra_ldap_filter:
        ldap_filter = f"(&{ldap_filter}{extra_ldap_filter})"
    
    fetch_attrs = attrs if attrs else list(_USER_LDAP.keys())
    raw_list = _fetch(
        search_base,
        ldap_filter,
        fetch_attrs,
    )
    if attrs: return raw_list # Skip mapping if specific attrs requested (usually for count)
    
    rows = []
    for a in raw_list:
        uac      = _attr(a, "userAccountControl")
        lockout  = _attr(a, "lockoutTime")
        photo    = _attr(a, "thumbnailPhoto")
        expires  = _attr(a, "accountExpires")
        smtp     = _attr_list(a, "proxyAddresses")
        mgr      = _attr(a, "manager")
        last_logon_dt = _filetime_to_dt(_attr(a, "lastLogonTimestamp"))
        pwd_dt        = _filetime_to_dt(_attr(a, "pwdLastSet"))

        row = {
            "username":               _attr(a, "sAMAccountName"),
            "display_name":           _attr(a, "displayName"),
            "first_name":             _attr(a, "givenName"),
            "last_name":              _attr(a, "sn"),
            "email":                  _attr(a, "mail"),
            "phone":                  _attr(a, "telephoneNumber"),
            "mobile":                 _attr(a, "mobile"),
            "home_phone":             _attr(a, "homePhone"),
            "fax":                    _attr(a, "facsimileTelephoneNumber"),
            "street":                 _attr(a, "streetAddress"),
            "city":                   _attr(a, "l"),
            "state":                  _attr(a, "st"),
            "postal_code":            _attr(a, "postalCode"),
            "country":                _attr(a, "co"),
            "department":             _attr(a, "department"),
            "job_title":              _attr(a, "title"),
            "company":                _attr(a, "company"),
            "manager":                _parse_dn_cn(mgr),
            "employee_id":            _attr(a, "employeeID"),
            "employee_number":        _attr(a, "employeeNumber"),
            "upn":                    _attr(a, "userPrincipalName"),
            "profile_path":           _attr(a, "profilePath"),
            "logon_script":           _attr(a, "scriptPath"),
            "home_directory":         _attr(a, "homeDirectory"),
            "home_drive":             _attr(a, "homeDrive"),
            "description":            _attr(a, "description"),
            "notes":                  _attr(a, "info"),
            "disabled":               _uac_disabled(uac),
            "account_locked":         _uac_locked(lockout),
            "bad_password_count":     _attr(a, "badPwdCount"),
            "logon_count":            _attr(a, "logonCount"),
            "last_logon":             last_logon_dt,
            "password_last_set":      pwd_dt,
            "account_expires":        _filetime_to_dt(expires),
            "creation_date":          _attr(a, "whenCreated"),
            "modification_date":      _attr(a, "whenChanged"),
            "group_membership_direct":[_parse_dn_cn(g) for g in _attr_list(a, "memberOf")],
            "password_never_expires": _uac_pwd_never_expires(uac),
            "smtp_addresses":         [s for s in smtp if s and s.startswith("SMTP:")],
            "hidden_from_gal":        bool(_attr(a, "msExchHideFromAddressLists")),
            "has_photo":              bool(photo),
            "distinguished_name":     _attr(a, "distinguishedName"),
            "guid":                   str(_attr(a, "objectGUID") or ""),
            "sid":                    str(_attr(a, "objectSid") or ""),
            # computed helpers (prefix _ ไม่ return ให้ client)
            "_last_logon_days":       _days_ago(last_logon_dt),
            "_pwd_days":              _days_ago(pwd_dt),
            "_parent_container":      ",".join(str(_attr(a,"distinguishedName") or "").split(",")[1:]),
        }
        rows.append(row)
    return rows


def _build_computers(search_base: str, member_of_dn: str | None = None, attrs: list[str] | None = None, where_f: dict | None = None) -> list[dict]:
    ldap_filter = "(objectClass=computer)"
    if member_of_dn:
        ldap_filter = f"(&(objectClass=computer)(memberOf:1.2.840.113556.1.4.1941:={member_of_dn}))"
    
    if where_f:
        pushed = _build_pushed_ldap_filter(where_f, _COMPUTER_LDAP_REV)
        if pushed:
            ldap_filter = f"(&{ldap_filter}{pushed})"
        
    fetch_attrs = attrs if attrs else list(_COMPUTER_LDAP.keys())
    raw_list = _fetch(
        search_base,
        ldap_filter,
        fetch_attrs,
    )
    if attrs: return raw_list
    
    rows = []
    for a in raw_list:
        uac = _attr(a, "userAccountControl")
        ll  = _filetime_to_dt(_attr(a, "lastLogonTimestamp"))
        pwd = _filetime_to_dt(_attr(a, "pwdLastSet"))
        row = {
            "name":                   _attr(a, "cn"),
            "dns_hostname":           _attr(a, "dNSHostName"),
            "operating_system":       _attr(a, "operatingSystem"),
            "os_version":             _attr(a, "operatingSystemVersion"),
            "service_pack":           _attr(a, "operatingSystemServicePack"),
            "description":            _attr(a, "description"),
            "managed_by":             _parse_dn_cn(_attr(a, "managedBy")),
            "disabled":               _uac_disabled(uac),
            "last_logon":             ll,
            "password_last_changed":  pwd,
            "creation_date":          _attr(a, "whenCreated"),
            "modification_date":      _attr(a, "whenChanged"),
            "group_membership_direct":[_parse_dn_cn(g) for g in _attr_list(a, "memberOf")],
            "distinguished_name":     _attr(a, "distinguishedName"),
            "guid":                   str(_attr(a, "objectGUID") or ""),
            "sid":                    str(_attr(a, "objectSid") or ""),
            "_last_logon_days":       _days_ago(ll),
            "_pwd_days":              _days_ago(pwd),
            "_parent_container":      ",".join(str(_attr(a,"distinguishedName") or "").split(",")[1:]),
        }
        rows.append(row)
    return rows


def _build_contacts(search_base: str, attrs: list[str] | None = None, where_f: dict | None = None) -> list[dict]:
    ldap_filter = "(objectClass=contact)"
    if where_f:
        pushed = _build_pushed_ldap_filter(where_f, _CONTACT_LDAP_REV)
        if pushed:
            ldap_filter = f"(&{ldap_filter}{pushed})"

    fetch_attrs = attrs if attrs else list(_CONTACT_LDAP.keys())
    raw_list = _fetch(
        search_base,
        ldap_filter,
        fetch_attrs,
    )
    if attrs: return raw_list
    rows = []
    for a in raw_list:
        row = {
            "name":                   _attr(a, "cn"),
            "display_name":           _attr(a, "displayName"),
            "first_name":             _attr(a, "givenName"),
            "last_name":              _attr(a, "sn"),
            "email":                  _attr(a, "mail"),
            "phone":                  _attr(a, "telephoneNumber"),
            "mobile":                 _attr(a, "mobile"),
            "fax":                    _attr(a, "facsimileTelephoneNumber"),
            "company":                _attr(a, "company"),
            "department":             _attr(a, "department"),
            "job_title":              _attr(a, "title"),
            "street":                 _attr(a, "streetAddress"),
            "city":                   _attr(a, "l"),
            "country":                _attr(a, "co"),
            "office":                 _attr(a, "physicalDeliveryOfficeName"),
            "web_page":               _attr(a, "wWWHomePage"),
            "description":            _attr(a, "description"),
            "group_membership_direct":[_parse_dn_cn(g) for g in _attr_list(a, "memberOf")],
            "creation_date":          _attr(a, "whenCreated"),
            "modification_date":      _attr(a, "whenChanged"),
            "distinguished_name":     _attr(a, "distinguishedName"),
            "guid":                   str(_attr(a, "objectGUID") or ""),
        }
        rows.append(row)
    return rows


def _build_groups(search_base: str, member_of_dn: str | None = None, attrs: list[str] | None = None, where_f: dict | None = None) -> list[dict]:
    ldap_filter = "(objectClass=group)"
    if member_of_dn:
        ldap_filter = f"(&(objectClass=group)(memberOf:1.2.840.113556.1.4.1941:={member_of_dn}))"

    if where_f:
        pushed = _build_pushed_ldap_filter(where_f, _GROUP_LDAP_REV)
        if pushed:
            ldap_filter = f"(&{ldap_filter}{pushed})"

    fetch_attrs = attrs if attrs else list(_GROUP_LDAP.keys())
    raw_list = _fetch(
        search_base,
        ldap_filter,
        fetch_attrs,
    )
    if attrs: return raw_list
    rows = []
    for a in raw_list:
        gtype, scope = _group_type(_attr(a, "groupType"))
        members      = _attr_list(a, "member")
        row = {
            "name":                   _attr(a, "cn"),
            "description":            _attr(a, "description"),
            "group_type":             gtype,
            "group_scope":            scope,
            "members_direct":         [_parse_dn_cn(m) for m in members],
            "member_count":           len(members),
            "managed_by":             _parse_dn_cn(_attr(a, "managedBy")),
            "email":                  _attr(a, "mail"),
            "creation_date":          _attr(a, "whenCreated"),
            "modification_date":      _attr(a, "whenChanged"),
            "distinguished_name":     _attr(a, "distinguishedName"),
            "guid":                   str(_attr(a, "objectGUID") or ""),
        }
        rows.append(row)
    return rows


def _build_ous(search_base: str, attrs: list[str] | None = None, where_f: dict | None = None) -> list[dict]:
    ldap_filter = "(objectClass=organizationalUnit)"
    if where_f:
        pushed = _build_pushed_ldap_filter(where_f, _OU_LDAP_REV)
        if pushed:
            ldap_filter = f"(&{ldap_filter}{pushed})"

    fetch_attrs = attrs if attrs else list(_OU_LDAP.keys())
    raw_list = _fetch(
        search_base,
        ldap_filter,
        fetch_attrs,
    )
    if attrs: return raw_list
    rows = []
    for a in raw_list:
        row = {
            "name":               _attr(a, "ou"),
            "description":        _attr(a, "description"),
            "linked_gpos":        _parse_gplink(_attr(a, "gPLink")),
            "has_gpo_linked":     bool(_attr(a, "gPLink")),
            "creation_date":      _attr(a, "whenCreated"),
            "modification_date":  _attr(a, "whenChanged"),
            "distinguished_name": _attr(a, "distinguishedName"),
            "guid":               str(_attr(a, "objectGUID") or ""),
        }
        rows.append(row)
    return rows

# ── Server-side filter engine ──────────────────────────────────────────────────

def _apply_filter(rows: list[dict], f: dict) -> list[dict]:
    """
    กรอง rows ด้วย Python — ไม่ต้องแปลงเป็น LDAP
    """
    max_pwd_age = _get_max_pwd_age() if "password_expired" in f else 0

    def _str(v: Any) -> str:
        return str(v or "").lower().strip()

    def _match(row: dict) -> bool:
        for key, val in f.items():
            if val is None:
                continue

            # ── boolean / attribute checks ──────────────────────────────
            if key in ("disabled", "account_locked", "has_photo",
                       "has_gpo_linked", "hidden_from_gal"):
                if row.get(key) != bool(val):
                    return False
            elif key == "password_never_expires":
                if row.get("password_never_expires") != bool(val):
                    return False
            elif key == "password_expired":
                if row.get("password_never_expires") or max_pwd_age == 0:
                    is_expired = False
                else:
                    pwd_days = row.get("_pwd_days")
                    is_expired = (pwd_days is not None and pwd_days > max_pwd_age)
                if is_expired != bool(val):
                    return False
            elif key == "no_manager":
                if bool(row.get("manager")) == bool(val):
                    return False
            elif key == "no_email":
                if bool(row.get("email")) == bool(val):
                    return False
            elif key == "is_empty":
                if (row.get("member_count") or 0) > 0 if val else False:
                    # if val is True, we want member_count == 0
                    if (row.get("member_count") or 0) != 0: return False

            # ── days thresholds ────────────────────────────────────────
            elif key == "last_logon_days":
                d = row.get("_last_logon_days")
                if d is None or d < int(val):
                    return False
            elif key == "pwd_days":
                d = row.get("_pwd_days")
                if d is None or d < int(val):
                    return False

            # ── member count ───────────────────────────────────────────
            elif key == "member_count_min":
                if (row.get("member_count") or 0) < int(val):
                    return False
            elif key == "member_count_max":
                if (row.get("member_count") or 0) > int(val):
                    return False

            # ── list fields ────────────────────────────────────────────
            elif key == "member_of":
                groups = [_str(g) for g in (row.get("group_membership_direct") or [])]
                if not any(_str(val) in g for g in groups):
                    return False
            elif key == "members_has":
                members = [_str(m) for m in (row.get("members_direct") or [])]
                if not any(_str(val) in m for m in members):
                    return False

            # ── string operators ───────────────────────────────────────
            elif key.endswith("_contains"):
                field = key[:-9]
                if _str(val) not in _str(row.get(field)):
                    return False
            elif key.endswith("_startswith"):
                field = key[:-11]
                if not _str(row.get(field)).startswith(_str(val)):
                    return False
            elif key.endswith("_endswith"):
                field = key[:-9]
                if not _str(row.get(field)).endswith(_str(val)):
                    return False
            elif key.endswith("_regex"):
                field = key[:-6]
                if not re.search(_str(val), _str(row.get(field))):
                    return False
            elif key.endswith("_not"):
                field = key[:-4]
                if _str(row.get(field)) == _str(val):
                    return False

            # ── exact match (default) ──────────────────────────────────
            else:
                row_val = row.get(key)
                
                # Support OR (e.g. "IT|HR")
                if isinstance(val, str) and "|" in val:
                    options = [o.strip().lower() for o in val.split("|")]
                    if _str(row_val) not in options:
                        return False
                # Support Range (e.g. "30..90")
                elif isinstance(val, str) and ".." in val:
                    try:
                        start, end = val.split("..")
                        rv = int(row_val or 0)
                        if not (int(start) <= rv <= int(end)):
                            return False
                    except (ValueError, TypeError):
                        return False
                # Standard exact match
                else:
                    if _str(row_val) != _str(val):
                        return False

        return True

    return [r for r in rows if _match(r)]


def _select_fields(rows: list[dict], allowed: list[str] | None) -> list[dict]:
    """คืนเฉพาะ field ที่ระบุ (ตัด _computed fields ออกด้วยเสมอ)"""
    if allowed is None:
        return [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    return [{k: v for k, v in r.items() if k in allowed} for r in rows]


def _parse_where(where_str: str) -> dict:
    """แปลง where string ("key=val, key_contains=val") -> dict filter"""
    if not where_str or not where_str.strip():
        return {}
    
    import ast
    # ลองเช็คว่าเป็น JSON หรือ Dictionary string หรือไม่ (เผื่อ AI ส่งมาแบบเดิม)
    s = where_str.strip()
    if (s.startswith("{") and s.endswith("}")):
        try:
            return json.loads(s)
        except:
            try: return ast.literal_eval(s)
            except: pass

    # แยกด้วย comma
    parts = [p.strip() for p in s.split(",") if p.strip()]
    f = {}
    for p in parts:
        k, v = "", ""
        if "!=" in p:
            k, v = p.split("!=", 1)
            k = k.strip() + "_not"
            v = v.strip()
        elif "=" in p:
            k, v = p.split("=", 1)
            k, v = k.strip(), v.strip()
        
        if k:
            # แปลง LDAP key เป็น Friendly key (ดักทาง AI)
            base_k = k.replace("_contains", "").replace("_startswith", "").replace("_endswith", "").replace("_regex", "").replace("_not", "")
            if base_k in _ALIAS_MAP:
                k = k.replace(base_k, _ALIAS_MAP[base_k])

            # ตัด quotes ถ้ามี
            if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
                v = v[1:-1]
            
            # แปลง boolean/int (ยกเว้นที่มี | หรือ ..)
            lv = v.lower()
            if lv == "true": f[k] = True
            elif lv == "false": f[k] = False
            elif v.isdigit() and "|" not in v and ".." not in v: 
                f[k] = int(v)
            else:
                f[k] = v
    return f


def _build_pushed_ldap_filter(f: dict, rev_map: dict) -> str:
    """แปลง filter พื้นฐานใน dict เป็น LDAP filter string เพื่อ push-down ไปที่ server."""
    if not f:
        return ""
    
    clauses = []
    for k, v in f.items():
        base_k = k
        op = "="
        suffix = ""
        
        # คัดกรองเฉพาะ operators ที่ LDAP รองรับโดยตรง
        if k.endswith("_contains"):
            base_k = k[:-9]
            op = "="
            v = f"*{v}*"
        elif k.endswith("_startswith"):
            base_k = k[:-11]
            op = "="
            v = f"{v}*"
        elif k.endswith("_endswith"):
            base_k = k[:-9]
            op = "="
            v = f"*{v}"

        ldap_attr = rev_map.get(base_k)
        if not ldap_attr:
            continue
            
        # จัดการค่าที่เป็น boolean/int
        if isinstance(v, bool):
            continue # boolean มักติด UAC bitwise คัดกรองใน Python ชัวร์กว่า
        
        # กันอักขระพิเศษใน LDAP filter (เบื้องต้น)
        sv = str(v).replace("(", r"\28").replace(")", r"\29").replace("*", r"\2a") if "*" not in str(v) else str(v)
        clauses.append(f"({ldap_attr}{op}{sv})")
    
    if not clauses:
        return ""
    if len(clauses) == 1:
        return clauses[0]
    return "(&" + "".join(clauses) + ")"


def _resolve_cols(fields_str: str, presets: dict) -> tuple[list[str] | None, str | None]:
    key = fields_str.strip()
    if key in presets:
        return presets[key], None
    field_list = [f.strip() for f in key.split(",") if f.strip()]
    return field_list, None

# ── Tools ──────────────────────────────────────────────────────────────────────

@router.tool()
def list_ou_structure() -> str:
    """แสดงโครงสร้าง OU หลักของเครือ AAPICO และ ou_key ที่ใช้ระบุ scope ได้

    เรียกก่อน get_users / get_computers / get_contacts / get_groups / get_ous
    เพื่อเลือก ou_key ที่ตรงกับบริษัทหรือหมวดหมู่ที่ต้องการ
    
    *เคล็ดลับสำหรับ AI:* 1. สามารถใช้ Full DN (เช่น "OU=IT,OU=AH,DC=aapico,DC=com") เป็น ou_key ได้โดยตรงหากต้องการเจาะจง Sub-OU
    2. สามารถเลือก OU บริษัท (เช่น "ah") แล้วใช้ filter {"department": "IT"} แทนได้

    Returns:
        JSON: { ou_key: { dn, description } }
    """
    meta = {
        "all":              {"dn": _OU_MAP["all"],              "description": "ดึงข้อมูลทั้ง Domain (aapico.com)"},
        "all_users":        {"dn": _OU_MAP["all_users"],        "description": "Users พื้นฐานทั้งหมด (CN=Users)"},
        
        # บริษัทในเครือ
        "aa":               {"dn": _OU_MAP["aa"],               "description": "บริษัท AA"},
        "ac":               {"dn": _OU_MAP["ac"],               "description": "บริษัท AC"},
        "ah":               {"dn": _OU_MAP["ah"],               "description": "บริษัท AH (มีแผนกย่อยเช่น IT, Production)"},
        "aha":              {"dn": _OU_MAP["aha"],              "description": "บริษัท AHA (JIG Design/Making)"},
        "ahp":              {"dn": _OU_MAP["ahp"],              "description": "บริษัท AHP (Assy, Press)"},
        "ahr":              {"dn": _OU_MAP["ahr"],              "description": "บริษัท AHR"},
        "aht":              {"dn": _OU_MAP["aht"],              "description": "บริษัท AHT (Die Engineering/Making)"},
        "aits":             {"dn": _OU_MAP["aits"],             "description": "บริษัท AITS (AI, FDC, Location Intelligence)"},
        "al":               {"dn": _OU_MAP["al"],               "description": "บริษัท AL"},
        "ap":               {"dn": _OU_MAP["ap"],               "description": "บริษัท AP"},
        "apr":              {"dn": _OU_MAP["apr"],              "description": "บริษัท APR"},
        "as_group":         {"dn": _OU_MAP["as_group"],         "description": "บริษัท AS"},
        "asp":              {"dn": _OU_MAP["asp"],              "description": "บริษัท ASP"},
        
        # ส่วนกลาง
        "contacts":         {"dn": _OU_MAP["contacts"],         "description": "External Contacts / Vendors (แบ่งตามบริษัทย่อยข้างใน)"},
        "managed_desktop":  {"dn": _OU_MAP["managed_desktop"],  "description": "Managed Devices / AzureAD Hybrid Devices"},
        "managed_groups":   {"dn": _OU_MAP["managed_groups"],   "description": "Distribution & Security Groups ส่วนกลาง"},
        "showroom":         {"dn": _OU_MAP["showroom"],         "description": "Showroom (AM, NESC, TSR)"},
    }
    return _json(meta)



@router.tool()
def count_objects(
    object_type: str,
    where:       str = "",
    ou_key:      str = "all",
) -> str:
    """นับจำนวน object ตามเงื่อนไข (no data fetch).
    
    Args:
        object_type: "user" | "computer" | "contact" | "group" | "ou"
        where:  เงื่อนไขกรอง e.g. "department=IT" | "disabled=false"
        ou_key: รหัส OU — ดูจาก list_ou_structure()
    """
    if not ou_key or ou_key.strip() == "":
        ou_key = "all"
    
    base, err = _resolve_ou(ou_key)
    if err:
        return err
    try:
        f = _parse_where(where)
        
        # Optimized path for simple counts (no filter)
        if not f:
            if object_type == "user":
                ldap_filter = "(&(objectClass=user)(objectCategory=person))"
            elif object_type == "computer":
                ldap_filter = "(objectClass=computer)"
            elif object_type == "contact":
                ldap_filter = "(objectClass=contact)"
            elif object_type == "group":
                ldap_filter = "(objectClass=group)"
            elif object_type == "ou":
                ldap_filter = "(objectClass=organizationalUnit)"
            else:
                return f"Unknown object_type: '{object_type}'"
            
            return str(_fetch_count(base, ldap_filter))

        # Path for filtered counts
        target_attrs = None # Fetch full attributes to apply Python filtering
        if object_type == "user":
            rows = _build_users(base, attrs=target_attrs, where_f=f)
        elif object_type == "computer":
            rows = _build_computers(base, attrs=target_attrs, where_f=f)
        elif object_type == "contact":
            rows = _build_contacts(base, attrs=target_attrs, where_f=f)
        elif object_type == "group":
            rows = _build_groups(base, attrs=target_attrs, where_f=f)
        elif object_type == "ou":
            rows = _build_ous(base, attrs=target_attrs, where_f=f)
        else:
            return f"Unknown object_type: '{object_type}'"

        rows = _apply_filter(rows, f)
        return str(len(rows))
    except LDAPException as e:
        return f"LDAP Error: {e}"


@router.tool()
def search_users(
    q:     str,
    columns: str = "identity",
    ou_key:  str = "all",
    limit:   int = 100,
    offset:  int = 0,
) -> str:
    """ค้นหา User แบบ Full-text ข้ามหลาย Field (username, display_name, email, department, phone, mobile).
    
    ใช้เมื่อไม่แน่ใจว่าข้อมูลที่ต้องการอยู่ใน Field ไหน หรือต้องการค้นหาแบบ Google-style.
    
    Args:
        q:       คำค้นหา (e.g. "wajeepradit", "IT", "081-xxx")
        columns: Preset หรือ list of fields
        ou_key:  Scope การค้นหา
        limit:   จำนวนที่แสดง (max 500)
    """
    base, err = _resolve_ou(ou_key)
    if err: return err
    field_list, ferr = _resolve_cols(columns, _USER_PRESETS)
    if ferr: return ferr

    # Escape query for LDAP safety
    sq = q.replace("(", r"\28").replace(")", r"\29").replace("*", r"\2a")
    ldap_filter = (
        f"(|(sAMAccountName=*{sq}*)(displayName=*{sq}*)(mail=*{sq}*)"
        f"(department=*{sq}*)(telephoneNumber=*{sq}*)(mobile=*{sq}*)"
        f"(title=*{sq}*)(company=*{sq}*))"
    )
    
    try:
        # ใช้ extra_ldap_filter เพื่อ push-down ค้นหาลง LDAP โดยตรง
        rows = _build_users(base, extra_ldap_filter=ldap_filter)
        
        total_matched = len(rows)
        # Slicing for pagination
        paged_rows = rows[offset : offset + limit]
        
        return _wrap(_select_fields(paged_rows, field_list), limit, total_matched, offset)
    except Exception as e:
        return f"Error: {e}"

@router.tool()
def get_users(
    columns: str  = "identity",
    where:   str  = "",
    ou_key:  str  = "all",
    limit:   int  = 200,
    offset:  int  = 0,
    sort_by: str  = "",
    member_of_dn: str | None = None,
    thorough_logon: bool = False,
) -> str:
    """ดึงข้อมูล User จาก Active Directory (Read-Only)
    
    Args:
        columns: Preset หรือระบุชื่อ field
        where:   เงื่อนไขกรอง e.g. "department=IT" | "last_logon_days=30..90"
        ou_key:  รหัส OU
        limit:   จำนวน record ต่อหน้า (default 200)
        offset:  จุดเริ่มต้น (สำหรับ pagination หน้า 2, 3, ...)
        sort_by: ชื่อ field ที่ต้องการเรียง (e.g. "username", "-last_logon" สำหรับ DESC)
        thorough_logon: ถ้าเป็น True จะไล่เช็ค Last Logon จากทุก DC (ช้าลงแต่แม่นยำ)
    """
    base, err = _resolve_ou(ou_key)
    if err: return err
    field_list, ferr = _resolve_cols(columns, _USER_PRESETS)
    if ferr: return ferr
    
    try:
        f = _parse_where(where)
        rows = _build_users(base, member_of_dn=member_of_dn, where_f=f)
        
        if f:
            rows = _apply_filter(rows, f)
            
        total_matched = len(rows)

        if thorough_logon:
            # ทำเฉพาะชุดที่จะ return เพื่อประหยัดเวลา
            # แต่ถ้า sort_by last_logon ต้องทำทั้งหมด!
            if "last_logon" in sort_by:
                for r in rows:
                    latest = _get_latest_last_logon(r["distinguished_name"])
                    if latest:
                        r["last_logon"] = latest
                        r["_last_logon_days"] = _days_ago(latest)
            else:
                # เดี๋ยวค่อยทำหลัง slice หรือ? ไม่ได้ เพราะ slice คือ pagination
                # ถ้า user อยากได้ last logon จริงๆ มักจะกรองมาก่อนแล้ว
                for r in rows: # ทำทั้งหมดไปก่อน (parallel ช่วยอยู่)
                     latest = _get_latest_last_logon(r["distinguished_name"])
                     if latest:
                         r["last_logon"] = latest
                         r["_last_logon_days"] = _days_ago(latest)

        # Sorting
        if sort_by:
            reverse = sort_by.startswith("-")
            key = sort_by.lstrip("-")
            # Handle None values in sort
            rows.sort(key=lambda r: (r.get(key) is None, r.get(key) or ""), reverse=reverse)

        # Pagination
        paged_rows = rows[offset : offset + limit]
        
        return _wrap(_select_fields(paged_rows, field_list), limit, total_matched, offset)
    except LDAPException as e:
        return f"LDAP Error: {e}"


@router.tool()
def get_computers(
    columns: str  = "identity",
    where:   str  = "",
    ou_key:  str  = "all",
    limit:   int  = 200,
    offset:  int  = 0,
    sort_by: str  = "",
    member_of_dn: str | None = None,
    thorough_logon: bool = False,
) -> str:
    """ดึงข้อมูล Computer จาก Active Directory (Read-Only)"""
    base, err = _resolve_ou(ou_key)
    if err: return err
    field_list, ferr = _resolve_cols(columns, _COMPUTER_PRESETS)
    if ferr: return ferr
    try:
        f = _parse_where(where)
        rows = _build_computers(base, member_of_dn=member_of_dn, where_f=f)

        if f:
            rows = _apply_filter(rows, f)
        
        total_matched = len(rows)

        if thorough_logon:
            for r in rows:
                latest = _get_latest_last_logon(r["distinguished_name"])
                if latest:
                    r["last_logon"] = latest
                    r["_last_logon_days"] = _days_ago(latest)

        if sort_by:
            reverse = sort_by.startswith("-")
            key = sort_by.lstrip("-")
            rows.sort(key=lambda r: (r.get(key) is None, r.get(key) or ""), reverse=reverse)

        paged_rows = rows[offset : offset + limit]
        return _wrap(_select_fields(paged_rows, field_list), limit, total_matched, offset)
    except LDAPException as e:
        return f"LDAP Error: {e}"

@router.tool()
def get_gpos(limit: int = 500, offset: int = 0, sort_by: str = "") -> str:
    """List all Group Policy Objects (GPOs) in the domain."""
    base = f"CN=Policies,CN=System,{_AD_BASE_DN}"
    attrs = ["displayName", "whenCreated", "whenChanged", "gPCFileSysPath"]
    try:
        raw = _fetch(base, "(objectClass=groupPolicyContainer)", attrs, limit=5000)
        results = []
        for a in raw:
            results.append({
                "name": _attr(a, "displayName"),
                "creation_date": _attr(a, "whenCreated"),
                "modification_date": _attr(a, "whenChanged"),
                "sysvol_path": _attr(a, "gPCFileSysPath"),
            })
        
        total_matched = len(results)
        if sort_by:
            reverse = sort_by.startswith("-")
            key = sort_by.lstrip("-")
            results.sort(key=lambda r: (r.get(key) is None, r.get(key) or ""), reverse=reverse)
            
        paged_rows = results[offset : offset + limit]
        return _wrap(paged_rows, limit, total_matched, offset)
    except Exception as e:
        return f"Error: {e}"

@router.tool()
def get_domain_policy() -> str:
    """Retrieve Domain Password and Lockout Policies."""
    try:
        conn = _connect()
        conn.search(_AD_BASE_DN, "(objectClass=*)", attributes=["maxPwdAge", "minPwdLength", "lockoutDuration", "lockoutThreshold"], search_scope=SUBTREE)
        if not conn.entries:
            return "No domain policy found."
        
        e = conn.entries[0]
        # AD stores durations as negative 100ns intervals
        def _parse_duration(val):
            if not val: return None
            return abs(int(val)) // 10000000 // 60  # in minutes
            
        return _json({
            "max_password_age_days": (_parse_duration(e.maxPwdAge.value) or 0) // 1440 if e.maxPwdAge.value else "Never",
            "min_password_length": e.minPwdLength.value,
            "lockout_threshold": e.lockoutThreshold.value,
            "lockout_duration_mins": _parse_duration(e.lockoutDuration.value),
        })
    except Exception as e:
        return f"Error: {e}"

@router.tool()
def get_domain_summary() -> str:
    """General domain information, FSMO roles (PDC), and Functional Levels."""
    try:
        conn = _connect()
        # Find PDC
        conn.search(_AD_BASE_DN, "(objectClass=*)", attributes=["fSMORoleOwner"], search_scope=SUBTREE)
        pdc = "Unknown"
        if conn.entries:
            pdc = _parse_dn_cn(conn.entries[0].fSMORoleOwner.value)
            
        return _json({
            "domain_dn": _AD_BASE_DN,
            "primary_domain_controller": pdc,
            "configured_dcs": _AD_HOSTS,
        })
    except Exception as e:
        return f"Error: {e}"


@router.tool()
def get_contacts(
    columns: str  = "full",
    where:   str  = "",
    ou_key:  str  = "all",
    limit:   int  = 200,
    offset:  int  = 0,
    sort_by: str  = "",
) -> str:
    """ดึงข้อมูล Contact (External) จาก Active Directory (Read-Only)"""
    base, err = _resolve_ou(ou_key)
    if err: return err
    field_list, ferr = _resolve_cols(columns, _CONTACT_PRESETS)
    if ferr: return ferr
    try:
        f = _parse_where(where)
        rows = _build_contacts(base, where_f=f)
        if f:
            rows = _apply_filter(rows, f)
        
        total_matched = len(rows)
        if sort_by:
            reverse = sort_by.startswith("-")
            key = sort_by.lstrip("-")
            rows.sort(key=lambda r: (r.get(key) is None, r.get(key) or ""), reverse=reverse)

        paged_rows = rows[offset : offset + limit]
        return _wrap(_select_fields(paged_rows, field_list), limit, total_matched, offset)
    except LDAPException as e:
        return f"LDAP Error: {e}"


@router.tool()
def get_groups(
    columns: str  = "min",
    where:   str  = "",
    ou_key:  str  = "all",
    limit:   int  = 200,
    offset:  int  = 0,
    sort_by: str  = "",
) -> str:
    """ดึงข้อมูล Group จาก Active Directory (Read-Only)"""
    base, err = _resolve_ou(ou_key)
    if err: return err
    field_list, ferr = _resolve_cols(columns, _GROUP_PRESETS)
    if ferr: return ferr
    try:
        f = _parse_where(where)
        rows = _build_groups(base, where_f=f)
        if f:
            rows = _apply_filter(rows, f)
        
        total_matched = len(rows)
        if sort_by:
            reverse = sort_by.startswith("-")
            key = sort_by.lstrip("-")
            rows.sort(key=lambda r: (r.get(key) is None, r.get(key) or ""), reverse=reverse)

        paged_rows = rows[offset : offset + limit]
        return _wrap(_select_fields(paged_rows, field_list), limit, total_matched, offset)
    except LDAPException as e:
        return f"LDAP Error: {e}"


@router.tool()
def get_ous(
    columns: str  = "full",
    where:   str  = "",
    ou_key:  str  = "all",
    limit:   int  = 500,
    offset:  int  = 0,
    sort_by: str  = "",
) -> str:
    """ดึงข้อมูล OU / Container จาก Active Directory (Read-Only)"""
    base, err = _resolve_ou(ou_key)
    if err: return err
    field_list, ferr = _resolve_cols(columns, _OU_PRESETS)
    if ferr: return ferr
    try:
        f = _parse_where(where)
        rows = _build_ous(base, where_f=f)
        if f:
            rows = _apply_filter(rows, f)
        
        total_matched = len(rows)
        if sort_by:
            reverse = sort_by.startswith("-")
            key = sort_by.lstrip("-")
            rows.sort(key=lambda r: (r.get(key) is None, r.get(key) or ""), reverse=reverse)

        paged_rows = rows[offset : offset + limit]
        return _wrap(_select_fields(paged_rows, field_list), limit, total_matched, offset)
    except LDAPException as e:
        return f"LDAP Error: {e}"
