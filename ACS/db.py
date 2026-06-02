import pymysql

DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "imo password sa workbench sql",
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

def verify_login(email, password):
    """Return employee row if credentials match, else None."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM employees WHERE gmail = %s AND passw = %s",
        (email, password)
    )
    result = cursor.fetchone()
    conn.close()
    return result

def is_ip_banned(ip):
    """Return True if the IP is in the blacklist table."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM blacklist WHERE ip = %s", (ip,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def is_ip_recognized(ip):
    """Return True if the IP belongs to a known employee."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM employees WHERE ip = %s", (ip,))
    result = cursor.fetchone()
    conn.close()
    return result is not None
