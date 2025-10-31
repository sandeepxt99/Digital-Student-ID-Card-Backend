from flask import Flask 
from flask_cors import CORS
import os
import sys
from datetime import timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# from routes import all_blueprints  # Import from __init__.py
from routes import all_blueprints
app = Flask(__name__)
# CORS(app, supports_credentials=True)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_that_you_should_change')
app.permanent_session_lifetime = timedelta(days=30)



# Register all blueprints
for bp in all_blueprints:
    app.register_blueprint(bp)

# if __name__ == "__main__":
#   app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))



 
