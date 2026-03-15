import os
from flask import Flask
from config import config
from app.extensions import db, login_manager, migrate, csrf


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config['default']))

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    if not os.environ.get('VERCEL'):
        migrate.init_app(app, db)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.songs import songs_bp
    from app.routes.shows import shows_bp
    from app.routes.setlist import setlist_bp
    from app.routes.public import public_bp
    from app.routes.musicians import musicians_bp
    from app.routes.bands import bands_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(songs_bp, url_prefix='/songs')
    app.register_blueprint(shows_bp, url_prefix='/shows')
    app.register_blueprint(setlist_bp, url_prefix='/setlist')
    app.register_blueprint(public_bp, url_prefix='/p')
    app.register_blueprint(musicians_bp, url_prefix='/musicians')
    app.register_blueprint(bands_bp, url_prefix='/bands')

    # Root redirect
    from flask import redirect, url_for
    from flask_login import current_user

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('songs.index'))
        return redirect(url_for('auth.login'))

    return app
