import os
import json
from .router_core import MCPRouter
from ldap3 import Server, Connection, ALL, SUBTREE
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
AD_SERVER = os.getenv("AD_SERVER")
AD_USER = os.getenv("AD_USER")
AD_PASSWORD = os.getenv("AD_PASSWORD")
AD_BASE_DN = os.getenv("AD_BASE_DN")
AD_USE_SSL = os.getenv("AD_USE_SSL", "True").lower() == "true"

# Initialize MCP Router
router = MCPRouter("Active Directory")

def get_ad_connection():
    """Establishes a connection to the Active Directory."""
    if not all([AD_SERVER, AD_USER, AD_PASSWORD]):
        raise ValueError("Missing AD configuration variables (AD_SERVER, AD_USER, AD_PASSWORD)")

    try:
        server = Server(AD_SERVER, get_info=ALL, use_ssl=AD_USE_SSL)
        conn = Connection(server, user=AD_USER, password=AD_PASSWORD, auto_bind=True, read_only=True)
        return conn
    except Exception as e:
        raise RuntimeError(f"Error connecting to Active Directory: {e}")

@router.tool()
def search_users(query: str, attributes: list[str] = None) -> str:
    """
    Search for users in Active Directory.
    
    Args:
        query: The search string (e.g., 'john' will search for *john* in name, sAMAccountName, or mail)
        attributes: List of attributes to retrieve (default: ['cn', 'sAMAccountName', 'mail', 'department', 'title'])
    """
    conn = get_ad_connection()
    if attributes is None:
        attributes = ['cn', 'sAMAccountName', 'mail', 'department', 'title', 'telephoneNumber']
    
    search_filter = f"(&(objectClass=user)(objectCategory=person)(|(cn=*{query}*)(sAMAccountName=*{query}*)(mail=*{query}*)))"
    
    try:
        conn.search(search_base=AD_BASE_DN, 
                   search_filter=search_filter, 
                   search_scope=SUBTREE, 
                   attributes=attributes)
        
        if not conn.entries:
            return "No users found matching query."
            
        results = []
        for entry in conn.entries:
            results.append(json.loads(entry.entry_to_json()))
            
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error searching users: {e}"

@router.tool()
def get_user_details(username: str) -> str:
    """
    Get detailed information for a specific user by sAMAccountName.
    
    Args:
        username: The sAMAccountName of the user (e.g., 'jdoe')
    """
    conn = get_ad_connection()
    search_filter = f"(&(objectClass=user)(objectCategory=person)(sAMAccountName={username}))"
    
    try:
        conn.search(search_base=AD_BASE_DN, 
                   search_filter=search_filter, 
                   search_scope=SUBTREE, 
                   attributes=['*']) # Get all attributes
        
        if not conn.entries:
            return f"User '{username}' not found."
            
        # Returning only the first match
        return conn.entries[0].entry_to_json()
    except Exception as e:
        return f"Error getting user details: {e}"

@router.tool()
def list_group_members(group_name: str) -> str:
    """
    List all members of a specific AD group.
    
    Args:
        group_name: The name of the group (CN) to search for.
    """
    conn = get_ad_connection()
    # First find the group DN
    group_filter = f"(&(objectClass=group)(cn={group_name}))"
    
    try:
        conn.search(search_base=AD_BASE_DN, 
                   search_filter=group_filter, 
                   search_scope=SUBTREE, 
                   attributes=['distinguishedName', 'member'])
        
        if not conn.entries:
            return f"Group '{group_name}' not found."
        
        group_dn = conn.entries[0].distinguishedName.value
        
        # Now search for users who are members of this group
        # Using 'memberOf' attribute is often faster/easier than parsing 'member' attribute of the group
        member_filter = f"(&(objectClass=user)(memberOf={group_dn}))"
        
        conn.search(search_base=AD_BASE_DN, 
                   search_filter=member_filter, 
                   search_scope=SUBTREE, 
                   attributes=['cn', 'sAMAccountName', 'mail'])
                   
        results = []
        for entry in conn.entries:
            results.append({
                'name': str(entry.cn),
                'username': str(entry.sAMAccountName),
                'email': str(entry.mail)
            })
            
        return json.dumps(results, indent=2)
        
    except Exception as e:
        return f"Error listing group members: {e}"

if __name__ == "__main__":
    mcp.run()
