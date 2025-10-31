import io
import base64
from flask import Flask, request, jsonify, make_response, session  # Import session
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
import os  # Used for a good secret key

# --- Flask App Setup ---
app = Flask(__name__)
# Enable CORS for all routes and all origins
# We also need to add supports_credentials=True to allow cookies to be sent
CORS(app, supports_credentials=True)

# !!! REQUIRED FOR SESSIONS !!!
# A secret key is needed to securely sign the session cookie.
# In production, set this as an environment variable!
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_that_you_should_change')

# --- Mock Database (Same as before) ---
MOCK_STUDENTS_DB = [
    {"id": "s1", "name": "Alice Smith", "reg_no": "REG123", "roll_no": "R001", "course": "Computer Science"},
    {"id": "s2", "name": "Bob Johnson", "reg_no": "REG456", "roll_no": "R002", "course": "Physics"},
]
MOCK_TEACHERS_DB = [
    {"id": "t1", "name": "Prof. Davis", "email": "prof.davis@uni.edu", "phone": "111222333", "department": "Computer Science"},
    {"id": "t2", "name": "Dr. Eva", "email": "dr.eva@uni.edu", "phone": "123456789", "department": "Physics"},
]

# --- Database Functions (Same as before) ---
def student_at_db(reg_no=None, roll_no=None, user_id=None):
    for student in MOCK_STUDENTS_DB:
        if user_id and student["id"] == user_id:
            return student
        if reg_no and student["reg_no"] == reg_no:
            return student
        if roll_no and student["roll_no"] == roll_no:
            return student
    return None

def teacher_at_db(name=None, email=None, phone=None, user_id=None):
    if not (name or user_id):
        return None
    for teacher in MOCK_TEACHERS_DB:
        if user_id and teacher["id"] == user_id:
            return teacher
        if teacher["name"] == name:
            email_matches = email and teacher["email"] == email
            phone_matches = phone and teacher["phone"] == phone
            if email_matches or phone_matches:
                return teacher
    return None

# --- Image Helper (Same as before) ---
def create_dummy_image_base64(text, user_name, user_id):
    try:
        img = Image.new('RGB', (400, 250), color='#3498db') # Blue background
        d = ImageDraw.Draw(img)
        try:
            font_title = ImageFont.truetype("arial.ttf", 28)
            font_text = ImageFont.truetype("arial.ttf", 20)
        except IOError:
            font_title = ImageFont.load_default()
            font_text = ImageFont.load_default()
        d.text((20, 20), "University ID Card", fill=(255, 255, 255), font=font_title)
        d.text((20, 80), user_name, fill=(255, 255, 255), font=font_title)
        d.text((20, 120), f"ID: {user_id}", fill=(210, 210, 210), font=font_text)
        d.text((20, 160), text, fill=(210, 210, 210), font=font_text)
        d.rectangle([(300, 80), (380, 180)], outline=(255,255,255), width=2)
        d.text((310, 115), "PHOTO", fill=(255,255,255), font=font_text)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        img_base64 = base64.b64encode(buf.getvalue())
        return "data:image/png;base64," + img_base64.decode('utf-8')
    except Exception as e:
        print(f"Error creating dummy image: {e}")
        return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="

# --- API Endpoints ---

@app.route('/login/student', methods=['POST', 'OPTIONS'])
def login_student():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input, JSON expected"}), 400

    reg_no = data.get('registration_no')
    roll_no = data.get('college_rollno')

    student = student_at_db(reg_no=reg_no, roll_no=roll_no)

    if student:
        # --- LOGIN SUCCESS ---
        # Store user info in the session
        session['user_id'] = student['id']
        session['user_type'] = 'student'
        session.permanent = True
        id_card_front_b64 = create_dummy_image_base64(
            "ID Card - Front", student['name'], student['id']
        )
        id_card_back_b64 = create_dummy_image_base64(
            "ID Card - Back (Terms)", student['name'], student['id']
        )

        response_data = {
            "status": "success",
            "user_type": "student",
            "user_data": student,
            "other_required_data": {
                "message": f"Welcome, {student['name']}! You are now logged in.",
            },
            "id_images_base64": {
                "front": id_card_front_b64,
                "back": id_card_back_b64
            }
        }
        # The browser will automatically receive a 'session' cookie
        return jsonify(response_data), 200
    else:
        return jsonify({"error": "Student not found with provided credentials"}), 404

@app.route('/login/teacher', methods=['POST', 'OPTIONS'])
def login_teacher():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input, JSON expected"}), 400

    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')

    teacher = teacher_at_db(name=name, email=email, phone=phone)

    if teacher:
        # --- LOGIN SUCCESS ---
        # Store user info in the session
        session['user_id'] = teacher['id']
        session['user_type'] = 'teacher'

        id_card_front_b64 = create_dummy_image_base64(
            "ID Card - Front", teacher['name'], teacher['id']
        )
        id_card_back_b64 = create_dummy_image_base64(
            "ID Card - Back (Staff)", teacher['name'], teacher['id']
        )
        
        response_data = {
            "status": "success",
            "user_type": "teacher",
            "user_data": teacher,
            "other_required_data": {
                "message": f"Welcome, {teacher['name']}! You are now logged in.",
            },
            "id_images_base64": {
                "front": id_card_front_b64,
                "back": id_card_back_b64
            }
        }
        # The browser will automatically receive a 'session' cookie
        return jsonify(response_data), 200
    else:
        return jsonify({"error": "Teacher not found with provided credentials"}), 404

# --- NEW PROTECTED ROUTE ---
@app.route('/profile', methods=['GET'])
def get_profile():
    """
    A protected route that only works if the user is logged in (in session).
    """
    # Check if a user is "in the session"
    if 'user_id' in session and 'user_type' in session:
        user_id = session['user_id']
        user_type = session['user_type']
        
        user_data = None
        if user_type == 'student':
            user_data = student_at_db(user_id=user_id)
        elif user_type == 'teacher':
            user_data = teacher_at_db(user_id=user_id)

        if user_data:
            return jsonify({
                "status": "success",
                "logged_in_as": user_type,
                "user_data": user_data
            }), 200
        else:
            # Session is valid but user not in DB? Clear it.
            session.clear()
            return jsonify({"error": "User not found, session cleared"}), 404

    else:
        # If no 'user_id' in session, they are not logged in.
        return jsonify({"error": "Unauthorized. Please log in first."}), 401

# --- NEW LOGOUT ROUTE ---
@app.route('/logout', methods=['POST'])
def logout():
    """
    Clears the user's session.
    """
    # The session.clear() function removes all data from the session
    session.clear()
    return jsonify({"status": "success", "message": "You have been logged out."}), 200

def _build_cors_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "http://127.0.0.1:5000") # Be specific for credentials
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "POST,GET,OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true") # This is crucial
    return response

# --- Run the App ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)