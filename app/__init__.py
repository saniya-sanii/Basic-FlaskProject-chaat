# app/__init__.py

import os
from flask import Flask
from .db import close_db, init_db

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder = '../static')

    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'root'
    app.config['MYSQL_PASSWORD'] = ''
    app.config['MYSQL_DB'] = 'restaurant_db'
    
    # Initialize the database on startup
    init_db(app)
    
    # Register database connection teardown
    app.teardown_appcontext(close_db)

    from .routes import init_routes
    init_routes(app)

    return app


