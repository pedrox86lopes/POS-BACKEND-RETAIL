import os
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, session, g
import sqlite3
from database import get_db_connection, init_db
import json
from werkzeug.security import generate_password_hash, check_password_hash # For password handling
from functools import wraps # For creating decorators

# --- Load environment variables from .env file ---
from dotenv import load_dotenv
load_dotenv()
# --- End .env loading ---

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_fallback_secret_key_for_dev_only')

# Initialize the database when the application starts
with app.app_context():
    init_db()

# --- Authentication and Authorization Decorators ---

@app.before_request
def load_logged_in_user():
    """
    Loads the logged-in user's data from the session before each request.
    Stores it in Flask's 'g' object for easy access in routes and templates.
    """
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
        g.role = None
    else:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        g.user = user
        g.role = user['role'] if user else None # Store role for easy access

def login_required(view):
    """
    Decorator to ensure a user is logged in to access a route.
    Redirects to login page if not authenticated.
    """
    @wraps(view) # Preserves original function metadata
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped_view

def role_required(required_role):
    """
    Decorator to ensure a logged-in user has a specific role to access a route.
    Redirects to homepage with an error if role is insufficient.
    """
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if g.user is None:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('login'))
            
            # Check if the user's role matches the required role
            # For simplicity, 'manager' can do 'cashier' tasks, but not vice-versa
            if required_role == 'cashier' and g.role not in ['cashier', 'manager']:
                flash('You do not have sufficient permissions to access this page.', 'error')
                return redirect(url_for('index'))
            elif required_role == 'manager' and g.role != 'manager':
                flash('You do not have sufficient permissions to access this page.', 'error')
                return redirect(url_for('index'))

            return view(*args, **kwargs)
        return wrapped_view
    return decorator

# --- Authentication Routes ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session.clear() # Clear any existing session
            session['user_id'] = user['id'] # Store user ID in session
            flash(f'Welcome, {user["username"]}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Handles user logout."""
    session.clear() # Clear the session
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

# --- Web UI Routes (for displaying HTML pages) ---

@app.route('/')
@login_required # Requires user to be logged in
def index():
    """
    Renders the homepage, displaying all products.
    Also includes a form to add new products.
    """
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    # Pass g.user and g.role to the template for conditional rendering
    return render_template('index.html', products=products, user=g.user, role=g.role)

@app.route('/make_sale')
@login_required # Requires user to be logged in
@role_required('cashier') # Requires cashier or manager role
def make_sale_page():
    """
    Renders the page for making a new sale.
    Displays available products for selection.
    """
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template('make_sale.html', products=products, user=g.user, role=g.role)

@app.route('/sales_history')
@login_required # Requires user to be logged in
@role_required('cashier') # Requires cashier or manager role
def sales_history_page():
    """
    Renders the page displaying a list of all past sales.
    """
    conn = get_db_connection()
    sales = conn.execute('SELECT id, sale_date, total_amount FROM sales ORDER BY sale_date DESC').fetchall()
    conn.close()
    return render_template('sales_history.html', sales=sales, user=g.user, role=g.role)

# --- Backend API Endpoints (for processing data) ---

@app.route('/products', methods=['POST'])
@login_required # Requires user to be logged in
@role_required('manager') # Only managers can add products
def add_product():
    """
    API endpoint to add a new product.
    Expected form data: sku, name, price, stock_quantity.
    """
    sku = request.form['sku']
    name = request.form['name']
    price = request.form['price']
    stock_quantity = request.form['stock_quantity']

    if not sku or not name or not price or not stock_quantity:
        flash('All product fields are required!', 'error')
        return redirect(url_for('index'))
    try:
        price = float(price)
        stock_quantity = int(stock_quantity)
        if price <= 0 or stock_quantity < 0:
            flash('Price must be positive, stock quantity non-negative.', 'error')
            return redirect(url_for('index'))
    except ValueError:
        flash('Invalid price or stock quantity format.', 'error')
        return redirect(url_for('index'))

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO products (sku, name, price, stock_quantity) VALUES (?, ?, ?, ?)",
                       (sku, name, price, stock_quantity))
        conn.commit()
        flash(f'Product "{name}" added successfully!', 'success')
    except sqlite3.IntegrityError:
        flash(f'Product with SKU "{sku}" already exists. Please use a unique SKU.', 'error')
        conn.rollback()
    finally:
        conn.close()
    return redirect(url_for('index'))

@app.route('/process_sale', methods=['POST'])
@login_required # Requires user to be logged in
@role_required('cashier') # Requires cashier or manager role
def process_sale():
    """
    API endpoint to process a new sale.
    This is the core transactional logic.
    Expected JSON data: [{"product_sku": "SKU001", "quantity": 2}, ...]
    """
    try:
        items_data = request.json
        if not items_data:
            flash('No items provided for sale.', 'error')
            return jsonify({"error": "No items provided for sale"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        total_amount = 0
        sale_items_to_insert = []

        cursor.execute("BEGIN TRANSACTION")

        for item in items_data:
            product_sku = item.get('product_sku')
            quantity = item.get('quantity')

            if not product_sku or not isinstance(quantity, int) or quantity <= 0:
                raise ValueError(f"Invalid item data: {item}. SKU and positive quantity required.")

            product_row = cursor.execute('SELECT id, name, price, stock_quantity FROM products WHERE sku = ?', (product_sku,)).fetchone()

            if not product_row:
                raise ValueError(f"Product with SKU '{product_sku}' not found.")

            product_id = product_row['id']
            product_name = product_row['name']
            current_stock = product_row['stock_quantity']
            product_price = product_row['price']

            if current_stock < quantity:
                raise ValueError(f"Insufficient stock for '{product_name}' (SKU: {product_sku}). Available: {current_stock}, Requested: {quantity}")

            new_stock = current_stock - quantity
            cursor.execute('UPDATE products SET stock_quantity = ? WHERE id = ?', (new_stock, product_id))

            item_total = product_price * quantity
            total_amount += item_total
            sale_items_to_insert.append({
                'product_id': product_id,
                'quantity': quantity,
                'price_at_sale': product_price
            })

        cursor.execute("INSERT INTO sales (total_amount) VALUES (?)", (total_amount,))
        sale_id = cursor.lastrowid

        for item_data in sale_items_to_insert:
            cursor.execute("INSERT INTO sale_items (sale_id, product_id, quantity, price_at_sale) VALUES (?, ?, ?, ?)",
                           (sale_id, item_data['product_id'], item_data['quantity'], item_data['price_at_sale']))

        conn.commit()
        flash('Sale processed successfully!', 'success')
        return jsonify({"message": "Sale processed successfully", "sale_id": sale_id, "total_amount": total_amount}), 201

    except ValueError as e:
        conn.rollback()
        flash(f'Sale failed: {str(e)}', 'error')
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        conn.rollback()
        flash(f'An unexpected error occurred: {str(e)}', 'error')
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500
    finally:
        conn.close()


@app.route('/products/<string:sku>', methods=['PUT'])
@login_required # Requires user to be logged in
@role_required('manager') # Only managers can update products
def update_product(sku):
    """
    API endpoint to update an existing product by its SKU.
    Expected JSON data: name, price, stock_quantity (all fields are required for PUT).
    """
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided for update"}), 400

        name = data.get('name')
        price = data.get('price')
        stock_quantity = data.get('stock_quantity')

        if not all([name, price is not None, stock_quantity is not None]):
            return jsonify({"error": "Name, price, and stock_quantity are required fields for PUT update."}), 400

        try:
            price = float(price)
            stock_quantity = int(stock_quantity)
            if price <= 0 or stock_quantity < 0:
                return jsonify({"error": "Price must be positive, stock quantity non-negative."}), 400
        except ValueError:
            return jsonify({"error": "Invalid price or stock quantity format."}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE products SET name = ?, price = ?, stock_quantity = ? WHERE sku = ?",
                       (name, price, stock_quantity, sku))

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": f"Product with SKU '{sku}' not found."}), 404

        conn.commit()
        conn.close()
        return jsonify({"message": f"Product '{sku}' updated successfully."}), 200

    except Exception as e:
        print(f"An unexpected error occurred during product update: {e}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@app.route('/sales_api', methods=['GET'])
@login_required # Requires user to be logged in
@role_required('cashier') # Requires cashier or manager role
def get_all_sales_api():
    """
    API endpoint to get a list of all sales (for programmatic access).
    """
    conn = get_db_connection()
    sales_data = conn.execute('SELECT id, sale_date, total_amount FROM sales ORDER BY sale_date DESC').fetchall()
    conn.close()

    sales_list = [dict(sale) for sale in sales_data]
    return jsonify(sales_list)

@app.route('/sale/<int:sale_id>', methods=['GET'])
@login_required # Requires user to be logged in
@role_required('cashier') # Requires cashier or manager role
def get_sale_details_api(sale_id):
    """
    API endpoint to get details of a specific sale, including its items.
    """
    conn = get_db_connection()
    sale = conn.execute('SELECT id, sale_date, total_amount FROM sales WHERE id = ?', (sale_id,)).fetchone()

    if not sale:
        conn.close()
        return jsonify({"error": "Sale not found"}), 404

    sale_items = conn.execute('''
        SELECT si.quantity, si.price_at_sale, p.name as product_name, p.sku
        FROM sale_items si
        JOIN products p ON si.product_id = p.id
        WHERE si.sale_id = ?
    ''', (sale_id,)).fetchall()

    conn.close()

    sale_details = dict(sale)
    sale_details['items'] = [dict(item) for item in sale_items]

    return jsonify(sale_details)


if __name__ == '__main__':
    app.run(debug=True)