# app/routes.py
import os
from flask import render_template, request, session, jsonify, redirect, url_for, flash, abort
from .db import get_db
from werkzeug.utils import secure_filename

def init_routes(app):
    
    # Configure upload folder for food images
    UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'img')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
    
    # Helper to check allowed image extensions
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}

    # 1. Customer Route: Home Page
    @app.route('/')
    def home():
        db = get_db()
        cursor = db.cursor()
        
        # Fetch featured foods to display on home page (e.g. 3 random or top foods)
        cursor.execute("SELECT * FROM foods WHERE available = TRUE LIMIT 3")
        featured_foods = cursor.fetchall()
        
        return render_template('home.html', featured_foods=featured_foods)

    # 2. Customer Route: Table Menu
    @app.route('/menu/<int:table_no>')
    def menu(table_no):
        # Store table number in session
        session['table_no'] = table_no
        
        db = get_db()
        cursor = db.cursor()
        
        # Fetch all available food items
        cursor.execute("SELECT * FROM foods WHERE available = TRUE ORDER BY category, name")
        foods = cursor.fetchall()
        
        # Group foods by category for front-end rendering
        categories = ['Starters', 'Main Course', 'Fast Food', 'Drinks', 'Desserts']
        foods_by_category = {cat: [] for cat in categories}
        for food in foods:
            cat = food['category']
            if cat in foods_by_category:
                foods_by_category[cat].append(food)
            else:
                # Fallback in case of custom categories
                if cat not in foods_by_category:
                    foods_by_category[cat] = []
                foods_by_category[cat].append(food)
                
        # Get cart from session to pre-populate quantities
        cart = session.get('cart', {})
        
        return render_template(
            'menu.html',
            foods_by_category=foods_by_category,
            categories=[cat for cat in foods_by_category.keys() if len(foods_by_category[cat]) > 0],
            table_no=table_no,
            cart=cart
        )

    # 3. Customer Route: Update Cart (JSON Endpoint)
    @app.route('/update_cart', methods=['POST'])
    def update_cart():
        # Expects JSON data: { "food_id": quantity }
        cart_data = request.json
        if not isinstance(cart_data, dict):
            return jsonify({"success": False, "message": "Invalid cart data"}), 400
            
        # Clean up any zero quantities and convert keys to strings/ints
        cleaned_cart = {}
        for food_id_str, qty in cart_data.items():
            try:
                food_id = int(food_id_str)
                quantity = int(qty)
                if quantity > 0:
                    cleaned_cart[food_id] = quantity
            except (ValueError, TypeError):
                continue
                
        session['cart'] = cleaned_cart
        return jsonify({"success": True, "message": "Cart updated successfully"})

    # 4. Customer Route: View Cart Page
    @app.route('/cart')
    def cart_page():
        table_no = session.get('table_no')
        if not table_no:
            # If no table number in session, default to Table 1 or ask to scan QR
            table_no = 1
            session['table_no'] = table_no
            
        cart = session.get('cart', {})
        if not cart:
            return render_template('cart.html', cart_items=[], total=0, table_no=table_no)
            
        db = get_db()
        cursor = db.cursor()
        
        # Fetch food details for all items in the cart
        food_ids = list(cart.keys())
        format_strings = ','.join(['%s'] * len(food_ids))
        cursor.execute(f"SELECT * FROM foods WHERE id IN ({format_strings})", tuple(food_ids))
        foods = cursor.fetchall()
        
        cart_items = []
        total = 0
        for food in foods:
            food_id = food['id']
            qty = cart[food_id]
            subtotal = food['price'] * qty
            total += subtotal
            
            cart_item = {
                'id': food_id,
                'name': food['name'],
                'price': food['price'],
                'image': food['image'],
                'category': food['category'],
                'qty': qty,
                'subtotal': subtotal
            }
            cart_items.append(cart_item)
            
        return render_template(
            'cart.html',
            cart_items=cart_items,
            total=total,
            table_no=table_no
        )

    # 5. Customer Route: Place Order
    @app.route('/place_order', methods=['POST'])
    def place_order():
        table_no = request.form.get('table_number', type=int)
        if not table_no:
            table_no = session.get('table_no', 1)
            
        cart = session.get('cart', {})
        if not cart:
            flash('Your cart is empty!', 'danger')
            return redirect(url_for('cart_page'))
            
        db = get_db()
        try:
            cursor = db.cursor()
            
            # Fetch food items to calculate total and verify
            food_ids = list(cart.keys())
            format_strings = ','.join(['%s'] * len(food_ids))
            cursor.execute(f"SELECT * FROM foods WHERE id IN ({format_strings})", tuple(food_ids))
            foods = cursor.fetchall()
            
            total_price = 0
            food_prices = {}
            for food in foods:
                food_prices[food['id']] = food['price']
                total_price += food['price'] * cart[food['id']]
                
            # 1. Insert order
            cursor.execute(
                "INSERT INTO orders (table_number, total_price, status) VALUES (%s, %s, %s)",
                (table_no, total_price, 'Pending')
            )
            order_id = cursor.lastrowid
            
            # 2. Insert order items
            order_items_data = []
            for food_id, qty in cart.items():
                if food_id in food_prices:
                    order_items_data.append((order_id, food_id, qty))
                    
            cursor.executemany(
                "INSERT INTO order_items (order_id, food_id, quantity) VALUES (%s, %s, %s)",
                order_items_data
            )
            
            db.commit()
            
            # Clear the cart from session
            session.pop('cart', None)
            
            flash('Order placed successfully! Sending it to the kitchen...', 'success')
            return redirect(url_for('order_status', order_id=order_id))
            
        except Exception as e:
            print("Order Placement Error: ", e)
            db.rollback()
            flash('Failed to place order. Please try again.', 'danger')
            return redirect(url_for('cart_page'))

    # 6. Customer Route: View Order Status
    @app.route('/order_status/<int:order_id>')
    def order_status(order_id):
        db = get_db()
        cursor = db.cursor()
        
        # Fetch order details
        cursor.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
        order = cursor.fetchone()
        if not order:
            abort(404, description="Order not found")
            
        # Fetch order items
        cursor.execute("""
            SELECT oi.quantity, f.name, f.price, f.image
            FROM order_items oi
            JOIN foods f ON oi.food_id = f.id
            WHERE oi.order_id = %s
        """, (order_id,))
        items = cursor.fetchall()
        
        return render_template('order_status.html', order=order, items=items)

    # 7. Admin Route: Login Screen
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            
            db = get_db()
            cursor = db.cursor()
            cursor.execute("SELECT * FROM user WHERE username = %s AND password_hash = %s", (username, password))
            user = cursor.fetchone()
            
            if user:
                session['admin_logged_in'] = True
                session['admin_username'] = username
                flash('Welcome back, Admin!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password!', 'danger')
                
        return render_template('login.html')

    # 8. Admin Route: Logout Action
    @app.route('/logout')
    def logout():
        session.pop('admin_logged_in', None)
        session.pop('admin_username', None)
        flash('Logged out successfully.', 'info')
        return redirect(url_for('login'))

    # Helper decorator for admin routes
    def admin_required(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('admin_logged_in'):
                flash('Please log in to access the admin dashboard.', 'warning')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    # 9. Admin Route: Dashboard / Kitchen Panel
    @app.route('/admin')
    @app.route('/dashboard')
    @admin_required
    def dashboard():
        db = get_db()
        cursor = db.cursor()
        
        # Fetch all orders (newest first)
        cursor.execute("SELECT * FROM orders ORDER BY id DESC")
        orders = cursor.fetchall()
        
        # Fetch items for all active orders
        for order in orders:
            cursor.execute("""
                SELECT oi.quantity, f.name, f.price
                FROM order_items oi
                JOIN foods f ON oi.food_id = f.id
                WHERE oi.order_id = %s
            """, (order['id'],))
            order['items'] = cursor.fetchall()
            
        # Fetch all foods for management
        cursor.execute("SELECT * FROM foods ORDER BY category, name")
        foods = cursor.fetchall()
        
        # Calculate Analytics
        cursor.execute("SELECT COUNT(*) as count FROM orders WHERE status != 'Served'")
        active_orders_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT SUM(total_price) as sum FROM orders")
        total_revenue = cursor.fetchone()['sum'] or 0
        
        cursor.execute("SELECT COUNT(*) as count FROM foods WHERE available = FALSE")
        out_of_stock_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM orders")
        total_orders_count = cursor.fetchone()['count']
        
        analytics = {
            'active_orders': active_orders_count,
            'total_revenue': total_revenue,
            'out_of_stock': out_of_stock_count,
            'total_orders': total_orders_count
        }
        
        return render_template(
            'admin.html',
            orders=orders,
            foods=foods,
            analytics=analytics
        )

    # 10. Admin Route: Add Food Item
    @app.route('/add_food', methods=['POST'])
    @admin_required
    def add_food():
        name = request.form['name']
        price = int(request.form['price'])
        category = request.form['category']
        description = request.form['description']
        
        # Handle file upload
        file = request.files.get('image')
        image_path = 'img/Cheeseburger.png' # default fallback
        
        if file and file.filename != '':
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Create upload directory if missing
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = f"img/{filename}"
            else:
                flash('Invalid image format! Supported: png, jpg, jpeg, gif, svg, webp', 'danger')
                return redirect(url_for('dashboard'))
                
        db = get_db()
        try:
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO foods (name, price, image, category, description, available) VALUES (%s, %s, %s, %s, %s, TRUE)",
                (name, price, image_path, category, description)
            )
            db.commit()
            flash(f'Food item "{name}" added successfully!', 'success')
        except Exception as e:
            print("Add Food Error: ", e)
            db.rollback()
            flash('Failed to add food item.', 'danger')
            
        return redirect(url_for('dashboard'))

    # 11. Admin Route: Edit Food Item
    @app.route('/edit_food/<int:id>', methods=['GET', 'POST'])
    @admin_required
    def edit_food(id):
        db = get_db()
        cursor = db.cursor()
        
        if request.method == 'POST':
            name = request.form['name']
            price = int(request.form['price'])
            category = request.form['category']
            description = request.form['description']
            available = 'available' in request.form
            
            file = request.files.get('image')
            
            try:
                # If a new image is uploaded, update image path
                if file and file.filename != '':
                    if allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        image_path = f"img/{filename}"
                        
                        cursor.execute("""
                            UPDATE foods 
                            SET name = %s, price = %s, image = %s, category = %s, description = %s, available = %s
                            WHERE id = %s
                        """, (name, price, image_path, category, description, available, id))
                    else:
                        flash('Invalid image format. Keeping old image.', 'warning')
                        cursor.execute("""
                            UPDATE foods 
                            SET name = %s, price = %s, category = %s, description = %s, available = %s
                            WHERE id = %s
                        """, (name, price, category, description, available, id))
                else:
                    cursor.execute("""
                        UPDATE foods 
                        SET name = %s, price = %s, category = %s, description = %s, available = %s
                        WHERE id = %s
                    """, (name, price, category, description, available, id))
                    
                db.commit()
                flash('Food item updated successfully!', 'success')
                return redirect(url_for('dashboard'))
            except Exception as e:
                print("Edit Food Error: ", e)
                db.rollback()
                flash('Failed to update food item.', 'danger')
                return redirect(url_for('dashboard'))
                
        # GET request: fetch item details
        cursor.execute("SELECT * FROM foods WHERE id = %s", (id,))
        food = cursor.fetchone()
        if not food:
            abort(404)
            
        return render_template('edit_food.html', food=food)

    # 12. Admin Route: Delete Food Item
    @app.route('/delete_food/<int:id>', methods=['POST'])
    @admin_required
    def delete_food(id):
        db = get_db()
        try:
            cursor = db.cursor()
            cursor.execute("DELETE FROM foods WHERE id = %s", (id,))
            db.commit()
            flash('Food item deleted successfully!', 'success')
        except Exception as e:
            print("Delete Food Error: ", e)
            db.rollback()
            flash('Failed to delete food item. It might be linked to existing orders.', 'danger')
            
        return redirect(url_for('dashboard'))

    # 13. Admin Route: Update Order Status
    @app.route('/update_order_status/<int:id>', methods=['POST'])
    @admin_required
    def update_order_status(id):
        new_status = request.form.get('status')
        if new_status not in {'Pending', 'Preparing', 'Ready', 'Served'}:
            return jsonify({"success": False, "message": "Invalid status value"}), 400
            
        db = get_db()
        try:
            cursor = db.cursor()
            cursor.execute("UPDATE orders SET status = %s WHERE id = %s", (new_status, id))
            db.commit()
            flash(f"Order #{id} status updated to '{new_status}'", 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            print("Update Order Status Error: ", e)
            db.rollback()
            flash("Failed to update order status.", 'danger')
            return redirect(url_for('dashboard'))