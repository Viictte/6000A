from flask import Flask, render_template, send_from_directory
from flask_cors import CORS
import os
from routes.api_routes import api_bp
from config import Config

def create_app():
    """Create Flask Application"""
    # Get absolute paths
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(backend_dir)
    frontend_dir = os.path.join(project_root, 'frontend')
    
    app = Flask(__name__, 
                template_folder=os.path.join(frontend_dir, 'templates'),
                static_folder=os.path.join(frontend_dir, 'static'))
    
    app.config.from_object(Config)
    
    # Enable CORS
    CORS(app)
    
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Home route
    @app.route('/')
    def index():
        """Homepage"""
        return send_from_directory(frontend_dir, 'index.html')
    
    # Static file route - specifically for generated_comics
    @app.route('/static/generated_comics/<path:filename>')
    def generated_comics(filename):
        """Generated comic files"""
        comics_dir = os.path.join(frontend_dir, 'static', 'generated_comics')
        print(f"Requesting comic: {filename}")
        print(f"   From directory: {comics_dir}")
        
        full_path = os.path.join(comics_dir, filename)
        if not os.path.exists(full_path):
            print(f"   File not found: {full_path}")
            return "File not found", 404
        else:
            file_size = os.path.getsize(full_path)
            print(f"   File exists ({file_size/1024:.2f} KB)")
        
        return send_from_directory(comics_dir, filename)
    
    # General static files route
    @app.route('/static/<path:filename>')
    def static_files(filename):
        """Static file serving"""
        static_dir = os.path.join(frontend_dir, 'static')
        return send_from_directory(static_dir, filename)
    
    return app

if __name__ == '__main__':
    # Get paths
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(backend_dir)
    frontend_dir = os.path.join(project_root, 'frontend')
    comics_dir = os.path.join(frontend_dir, 'static', 'generated_comics')
    
    # Ensure data directories exist
    os.makedirs(os.path.join(backend_dir, 'data'), exist_ok=True)
    os.makedirs(comics_dir, exist_ok=True)
    
    app = create_app()
    
    app.run(debug=True, host='0.0.0.0', port=5002)