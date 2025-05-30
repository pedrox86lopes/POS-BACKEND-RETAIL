import sqlite3
from werkzeug.security import generate_password_hash # Import for password hashing

DATABASE_NAME = 'pos.db'

def get_db_connection():
    """Establishes and returns a database connection."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database with necessary tables, sample data, and users."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create products table (existing)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock_quantity INTEGER NOT NULL
        )
    ''')

    # Create sales table (existing)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_amount REAL NOT NULL
        )
    ''')

    # Create sale_items table (existing)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price_at_sale REAL NOT NULL,
            FOREIGN KEY (sale_id) REFERENCES sales(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')

    # --- NEW: Create users table ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('cashier', 'manager'))
        )
    ''')

    # Add sample products if they don't exist (existing)
    products_to_add = [
        ('SKU001', 'Apple (kg)', 2.50, 50),
        ('SKU002', 'Milk (1L)', 1.20, 100),
        ('SKU003', 'Bread', 3.00, 30),
        ('SKU004', 'Eggs (dozen)', 4.50, 40)
    ]
    for sku, name, price, stock in products_to_add:
        try:
            cursor.execute("INSERT INTO products (sku, name, price, stock_quantity) VALUES (?, ?, ?, ?)",
                           (sku, name, price, stock))
        except sqlite3.IntegrityError:
            pass # Product already exists

    # --- NEW: Add sample users if they don't exist ---
    # Hash passwords securely
    manager_password_hash = generate_password_hash("managerpass")
    cashier_password_hash = generate_password_hash("cashierpass")

    users_to_add = [
        ('manager', manager_password_hash, 'manager'),
        ('cashier', cashier_password_hash, 'cashier')
    ]
    for username, password_hash, role in users_to_add:
        try:
            cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                           (username, password_hash, role))
        except sqlite3.IntegrityError:
            pass # User already exists

    conn.commit()
    conn.close()
    print("Database initialized successfully with products and users.")

if __name__ == '__main__':
    # This block runs only when database.py is executed directly
    init_db()