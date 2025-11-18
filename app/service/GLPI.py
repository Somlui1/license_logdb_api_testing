
def get_connection():
    return mysql.connector.connect(
        host="172.17.0.3",
        port=3306,
        user="admin",
        password="root",
        database="glpi"
    )


def get_devices_by_tenant(name: Optional[str] = None, boolean: Optional[bool] = None):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)  # dictionary=True เพื่อให้ได้ dict แทน tuple
        sql = """
            SELECT b.comment, b.contact, b.contact_num,
                   b.date_creation, b.date_mod, b.entities_id, b.id, b.is_deleted, b.is_dynamic,
                   b.is_recursive, b.is_template, b.last_boot, b.last_inventory_update, b.name,
                   b.networks_id, b.otherserial, b.serial, b.template_name, b.ticket_tco,
                   b.users_id, b.users_id_tech, b.uuid,
                   g1.completename AS tech_group,
                   g2.completename AS user_group,
                   a.name AS autoupdate,
                   l.completename AS location,
                   m.name AS computermodel,
                   t.name AS computertype,
                   mf.name AS manufacturer,
                   s.completename AS assetstatus
            FROM glpi.glpi_computers b
            LEFT JOIN glpi.glpi_groups g1 ON b.groups_id_tech = g1.id
            LEFT JOIN glpi.glpi_groups g2 ON b.groups_id = g2.id
            LEFT JOIN glpi.glpi_autoupdatesystems a ON b.autoupdatesystems_id = a.id
            LEFT JOIN glpi.glpi_locations l ON b.locations_id = l.id
            LEFT JOIN glpi.glpi_computermodels m ON b.computermodels_id = m.id
            LEFT JOIN glpi.glpi_computertypes t ON b.computertypes_id = t.id
            LEFT JOIN glpi.glpi_manufacturers mf ON b.manufacturers_id = mf.id
            LEFT JOIN glpi.glpi_states s ON b.states_id = s.id
            WHERE 1 = 1
        """

        params = []
        if name:
            sql += " AND b.name LIKE %s"
            params.append(f"%{name}%")

        cursor.execute(sql, params)
        result = cursor.fetchall()

        if boolean is not None:
            return {"exists": bool(result)}

        return result

    except Error as e:
        return {"error": str(e)}

    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
