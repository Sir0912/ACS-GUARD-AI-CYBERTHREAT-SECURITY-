import pymysql

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Myservermybestfriend09941991294",
    "database": "innovex_2026"
}

def get_connection():
    return pymysql.connect(
        host=DB_CONFIG["host"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        database=DB_CONFIG["database"],
        cursorclass=pymysql.cursors.DictCursor
    )

def verify_login(gmail, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE gmail=%s AND passw=%s", (gmail, password))
    employee = cursor.fetchone()
    conn.close()
    
    if employee:
        # Check if it's a dict (dict-like) or tuple
        if isinstance(employee, dict):
            return {
                "gmail": employee.get("gmail"),
                "name": employee.get("name"),
                "ip": employee.get("ip")
            }
        else:
            # It's a tuple - access by index
            return {
                "gmail": employee[2],
                "name": employee[1],
                "ip": employee[3] if len(employee) > 3 else None
            }
    return None
def is_ip_banned(ip):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM dashboard WHERE ip = %s AND banned_ip = 1", (ip,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def is_ip_recognized(ip):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE ip = %s", (ip,))
    result = cursor.fetchone()
    conn.close()
    return result is not None