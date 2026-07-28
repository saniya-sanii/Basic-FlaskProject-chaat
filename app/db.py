# app/db.py

import pymysql
from flask import g, current_app

def get_db():
    if 'db' not in g:
        g.db = pymysql.connect(
            host=current_app.config['MYSQL_HOST'],
            user=current_app.config['MYSQL_USER'],
            password=current_app.config['MYSQL_PASSWORD'],
            database=current_app.config['MYSQL_DB'],
            cursorclass=pymysql.cursors.DictCursor
        )
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app):
    """
    Connects to MySQL without a database first to create restaurant_db if needed,
    then initializes the database tables and populates starter food items.
    """
    try:
        # 1. Connect without specifying database to create database if it doesn't exist
        conn = pymysql.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            cursorclass=pymysql.cursors.DictCursor
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {app.config['MYSQL_DB']}")
        conn.close()

        # 2. Connect specifying the database to create tables
        conn = pymysql.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DB'],
            cursorclass=pymysql.cursors.DictCursor
        )
        cursor = conn.cursor()

        # 3. Create foods table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS foods (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100),
                price INT,
                image VARCHAR(255),
                category VARCHAR(100),
                description TEXT,
                available BOOLEAN DEFAULT TRUE
            )
        """)

        # 4. Create orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                table_number INT,
                total_price INT,
                status VARCHAR(50) DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 5. Create order_items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id INT,
                food_id INT,
                quantity INT,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (food_id) REFERENCES foods(id) ON DELETE CASCADE
            )
        """)

        # 6. Create user table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL
            )
        """)

        # 7. Seed default admin if not exists
        cursor.execute("SELECT COUNT(*) as count FROM user")
        if cursor.fetchone()['count'] == 0:
            cursor.execute("INSERT INTO user (username, password_hash) VALUES (%s, %s)", ('admin', 'admin'))
            print("Database Seeding: Default admin user created successfully.")

        # 8. Seed default foods if not exists
        cursor.execute("SELECT COUNT(*) as count FROM foods")
        if cursor.fetchone()['count'] == 0:
            starter_foods = [
                (
                    "Paneer Tikka", 
                    150, 
                    "img/paneer_tikka.png", 
                    "Starters", 
                    "Tender cubes of fresh cottage cheese marinated in a spiced yoghurt mixture, skewered with onions and bell peppers, and roasted to golden perfection in a traditional clay oven."
                ),
                (
                    "Cheeseburger", 
                    120, 
                    "img/Cheeseburger.png", 
                    "Fast Food", 
                    "Juicy flame-grilled chicken patty topped with melted cheddar cheese, fresh lettuce, sliced tomatoes, and our signature sauce in a warm toasted brioche bun."
                ),
                (
                    "Pizza Margherita", 
                    250, 
                    "img/Pizza Margherita.png", 
                    "Fast Food", 
                    "Classic Italian thin-crust pizza loaded with premium mozzarella cheese, sweet vine-ripened tomato sauce, and garnished with fresh basil leaves and olive oil."
                ),
                (
                    "White Sauce Pasta", 
                    180, 
                    "img/White Sauce Pasta.png", 
                    "Main Course", 
                    "Creamy penne pasta cooked in a rich, buttery garlic parmesan sauce, tossed with mushrooms, green peas, and served with a sprinkle of fresh herbs."
                ),
                (
                    "Summer Mojito", 
                    90, 
                    "img/mojito.png", 
                    "Drinks", 
                    "A refreshing, ice-cold mocktail made with muddled fresh mint leaves, lime juice, pure cane sugar, and club soda, garnished with a lime wheel."
                ),
                (
                    "Chocolate Lava Cake", 
                    130, 
                    "img/chocolate_lava_cake.png", 
                    "Desserts", 
                    "Indulgent, warm chocolate cake with a rich, molten chocolate center that flows out upon the first bite, served with a dusting of powdered sugar."
                )
            ]
            cursor.executemany(
                "INSERT INTO foods (name, price, image, category, description, available) VALUES (%s, %s, %s, %s, %s, TRUE)",
                starter_foods
            )
            print("Database Seeding: Default food items created successfully.")

        conn.commit()
        conn.close()
        print("Database Auto-Initialization Completed Successfully!")

    except Exception as e:
        print("Database Auto-Initialization Warning:", e)
        print("Please ensure that your XAMPP MySQL database is running.")