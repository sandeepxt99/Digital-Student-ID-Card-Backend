from flask import Blueprint ,jsonify, send_file, make_response,request,session
import json
import sys
import os 
import base64
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from dotenv import load_dotenv
import random
import string

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.qr_code import make_qr_code
from utils.card import merge_svg_template_back, merge_svg_template_front
from db_connection import get_collection
from utils.email_service import send_email
from utils.upload_to_cloudiary import upload_file


student_bp = Blueprint('student', __name__, url_prefix='/student')

load_dotenv()  # Loads variables from .env into os.environ

JWT_SECRET = os.getenv("JWT_SECRET")

@student_bp.route('/login' ,methods=['POST'])
def login():


    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()

    print("finl")

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input, JSON expected"}), 400
 
    print(data)

    try:
        roll_no =data.get('roll_no','')
        registration_no =data.get('registration_no','')
        password =data.get('password','')

        print(roll_no,password,registration_no,"dam")

        # Validate input
        if not roll_no and not registration_no:
            return jsonify({"error": "Please provide either roll_no or registration_no"}), 400

        # Get collection
        student_collection = get_collection('student')

        # Build query
        query = { }
        if roll_no:
            query['roll_no'] = int(roll_no)
        elif registration_no:
            query['registration_no'] = registration_no

        # Fetch student
        student = student_collection.find_one(query)
        print("check")
        if not student:
            return jsonify({"message": "Student not found"}), 404

        # Convert ObjectId to string
        student['_id'] = str(student['_id'])

        print("check")

        student_db_password = student.get("password","")
        print(student_db_password)
        if not check_password_hash(student_db_password, password): 
            return jsonify({"error": "Invalid password"}), 401

        
        if student['profile'].strip() =='' or student['sign'].strip() == '' :
            return jsonify({"message": "No profile or sign found " , "user_id" : student['_id'], "type" : "student"}), 400


        # session['user_id'] = "123p"
        session['user_id'] = student['_id']
        print("check")

        session['user_type'] = 'student'
        print("check")

        session.permanent = True

        print("check")

        # making card
        print("befor card")
        print(student["issue_date"])

        make_card(student)
        
        svg_path_1 = "../tmp/student_id_card_front.svg"
        svg_path_2 = "../tmp/student_id_card_back.svg"
        print("check")

        # Read SVG files and encode in base64 (so they can be sent via JSON)
        def encode_svg(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")

        svg1 = encode_svg(svg_path_1)
        svg2 = encode_svg(svg_path_2)
        print("check")


        response = {
        "svg_files": {
            "front.svg": svg1,
            "back.svg": svg2
        },
        "message": "Student fetched successfully",
        "type" : "student"
        }

     

        return jsonify(response) ,200


    except Exception as e:
        return jsonify({"error": str(e)}), 500

  
  
#
@student_bp.route('/change-password', methods=['POST'])
def change_password():

    if 'user_id' in session and 'user_type' in session:
        user_id = session['user_id']
        user_type = session['user_type']

        if user_type!= "student" :
            session.clear()
            return jsonify({"error": "Unauthorised, session cleared"}), 404

        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            return jsonify({"status": "Failed", "message": "Passwords not matched."}), 400
        
        hashed_password = generate_password_hash(password)


 
        student_collection = get_collection('student')
        
        result = student_collection.update_one(
            {"_id" : ObjectId(user_id)},
            {"$set": {"password": hashed_password}}
        )

        print(result.matched_count, user_id)
        if result.matched_count==1:
            return jsonify({
                "status": "success",
                "message": "Password changed successfully"
            }), 200
        else:
            session.clear()
            return jsonify({"error": "User not found, session cleared"}), 404
    else:
        return jsonify({"error": "Unauthorized. Please log in first."}), 401




@student_bp.route('/get', methods=['GET'])
def get_student_credential():
    try:

        print("check one",request.get_data())
        roll_no =  request.args.get('roll_no')
        registration_no = request.args.get('registration_no')

        # Validate input
        if not roll_no and not registration_no:
            return jsonify({"error": "Please provide either roll_no or registration_no"}), 400

        # return jsonify({
        #     "message": f"""Credentials is sent to  successfully""",
        
        # }), 200
        # Get collection
        student_collection = get_collection('student')

        # Build query
        query = {}
        if roll_no:
            query['roll_no'] = int(roll_no)
        elif registration_no:
            query['registration_no'] = registration_no

        # Fetch student
        student = student_collection.find_one(query)

        if not student:
            return jsonify({"message": "Student not found"}), 404

        # Convert ObjectId to string
        student['_id'] = str(student['_id'])

        password = generate_password(8)


        hashed_password = generate_password_hash(password)

    
        # Update the password in the database
        result = student_collection.update_one(
            {"_id": ObjectId(student["_id"])},  # Filter by student ID
            {"$set": {"password": hashed_password}}
        )

        email_body = f""" 

        Dear {student["name"]},

        We hope you are doing well. Please find below your login credentials for accessing the student portal. Kindly keep this information confidential and do not share it with anyone.

        Student Details:

        Name: {student["name"]}

        Roll No: {student["roll_no"]}

        Registration No: {student["registration_no"]}

        Password: {password}

        You can use these credentials to log in at 
        https://5173-firebase-id-1760600822304.cluster-m7dwy2bmizezqukxkuxd55k5ka.cloudworkstations.dev/login.

        If you face any issues while logging in or need to reset your password, please contact the support team.

        Best regards,
        Digital Student ID Card Team

        """

        send_email("Digital Student ID Card - Student Login Credentials",email_body,student["email"])
        return jsonify({
            "message": f"""Credentials is sent to {student["email"]} successfully""",
        
        }), 200


    except Exception as e:
        return jsonify({"error": str(e)}), 500


 
@student_bp.route('/update', methods=['POST'])
def update_student():

 

    try:
        data = request.form  # Use form for file uploads
        files = request.files

        print(data,files)

        user_id = data.get('user_id', '')
        
        print(user_id)

        try:
            obj_id = ObjectId(user_id)
        except InvalidId:
            return jsonify({"error": "Invalid student ID"}), 400

        print(obj_id)

        if not obj_id :
            return jsonify({"error": "Please provide user ID"}), 400

        # Get collection
        student_collection = get_collection('student')

    
        student =  student_collection.find_one({'_id': obj_id})

        print(student)
        if not student:
            return jsonify({"message": "Student not found"}), 404

        

        update_fields = {}
        student['_id'] = str(student['_id'])
 
        # Upload photo if provided
        photo_url = "" 
        sign_url= ""

        if 'photo' in files:
            photo_file = files['photo']
            photo_resp = upload_file(photo_file, 'student')
            photo_url = photo_resp.get("secure_url")
            update_fields['profile'] = photo_url

        # Upload sign if provided
        if 'sign' in files:
            sign_file = files['sign']
            sign_resp = upload_file(sign_file, 'student',remove_bg=True)
            sign_url = sign_resp.get("secure_url")
            update_fields['sign'] = sign_url

        # Perform update in database
        if update_fields:
            student_collection.update_one({'_id': ObjectId(student['_id'])}, {'$set': update_fields})
        
        print(student)

        student["sign"] = sign_url
        student["profile"] = photo_url

        print(student)
        make_card(student)
        
        svg_path_1 = "../tmp/student_id_card_front.svg"
        svg_path_2 = "../tmp/student_id_card_back.svg"
        print("check")

        # Read SVG files and encode in base64 (so they can be sent via JSON)
        def encode_svg(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")

        svg1 = encode_svg(svg_path_1)
        svg2 = encode_svg(svg_path_2)
        print("check")


        response = {
        "svg_files": {
            "front.svg": svg1,
            "back.svg": svg2
        },
        "message": "Student fetched successfully",
        }

     

        return jsonify(response) ,200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

 



def generate_password(length=8):
    # Define the characters to choose from: only letters and digits
    characters = string.ascii_letters + string.digits
    # Randomly select `length` characters
    password = ''.join(random.choice(characters) for _ in range(length))
    return password





# @student_bp.route('/profile', methods=['GET'])
# def get_profile():
#     if 'user_id' in session and 'user_type' in session:
#         user_id = session['user_id']
#         user_type = session['user_type']

#         user_data = True

#         if user_data:
#             return jsonify({
#                 "status": "success",
#                 "logged_in_as": user_type,
#                 "user_data": user_data
#             }), 200
#         else:
#             session.clear()
#             return jsonify({"error": "User not found, session cleared"}), 404
#     else:
#         return jsonify({"error": "Unauthorized. Please log in first."}), 401


#     # --- LOGOUT ---
@student_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"status": "success", "message": "You have been logged out."}), 200


 




def make_card(student_data):
    # student_data = {
    # "_id": "68f9af90e4a148677a5a0cab",
    # "name": "Nisha Thakur",
    # "registration_no": "BCA20211010",
    # "email": "nisha.thakur@example.com",
    # "phone": 9876543219,
    # "father_name": "Dinesh Thakur",
    # "address": "101 Ring Rd, Indore",
    # "class": "BCA",
    # "valid_session": "2025-2028",
    # "roll_no":  110,
    # "dob": "2005-06-22",
    # "issue_date":  "2005-06-22",
    # "profile": "https://res.cloudinary.com/dr9w7oyqe/image/upload/v1760940404/student/ex32shyilciahvdrcyd7.png",
    # "sign": "https://res.cloudinary.com/dr9w7oyqe/image/upload/v1761220064/local_uploads/kmkyjzyfb3bla7lkoiqr.png",
    # "year": 1
    # }
    print(student_data["issue_date"])
    print(str(student_data["issue_date"])[:10])
    with open('other/college.json', 'r') as file:
        college_data = json.load(file)  # Load JSON data into a Python dictionary

    def ordinal(n):
        if 10 <= n % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{n}{suffix}"


    student_class = f"{student_data['class']} {ordinal(student_data['year'])} Year"

    make_qr_code({
       "roll_no" : student_data["roll_no"],
       "registration_no" : student_data["registration_no"],
       "type" : "student"
    })
    qr_code_url = "tmp/qrcode.png"

    merge_svg_template_front({
        "name": student_data["name"],
        "roll_no": str(student_data["roll_no"]),
        "class": student_class,
        "dob": str(student_data["dob"]),
        "father_name" : student_data["father_name"],
        "valid_session" : student_data["valid_session"],
        "address" : student_data["address"],
        "profile_url" : student_data["profile"],
        "student_sign_url" : student_data["sign"],

        "college_name" : college_data["college_name"],
        "college_logo_url" : college_data["college_logo_url"],
        "college_sign_url" : college_data["college_sign_url"]
    })


    print("making front card")

    merge_svg_template_back({
        "college_name" : college_data["college_name"],
        "college_line1" : college_data["college_line1"],
        "college_line2" : college_data["college_line2"],
        "college_contact" : str(college_data["college_contact"]),
        "footer-info" : college_data["footer-info"],

        "student_contact" :str( student_data["phone"]),
        "date_issued" : str(student_data["issue_date"])[:10],
        "qr_code_url" : qr_code_url 
    })

    return {
        "message": "Card generated successfully",
        "front_svg_path": "tmp/student_id_card_front.svg",
        "back_svg_path": "tmp/student_id_card_back.svg"
    }



# --- Helper for CORS preflight ---
def _build_cors_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "http://127.0.0.1:5000")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "POST,GET,OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response















# with open('other/college.json', 'r') as file:
#     college_data = json.load(file)  # Load JSON data into a Python dictionary



# from flask import request, jsonify, make_response, session
# from database import student_at_db, teacher_at_db
# from utils import create_dummy_image_base64


# def register_routes(app):
#     """
#     Registers all routes to the Flask app.
#     """

#     # --- LOGIN STUDENT ---
#     @app.route('/login/student', methods=['POST', 'OPTIONS'])
#     def login_student():
#         if request.method == 'OPTIONS':
#             return _build_cors_preflight_response()

#         data = request.get_json()
#         if not data:
#             return jsonify({"error": "Invalid input, JSON expected"}), 400

#         reg_no = data.get('registration_no')
#         roll_no = data.get('college_rollno')
#         student = student_at_db(reg_no=reg_no, roll_no=roll_no)

#         if student:
#             session['user_id'] = student['id']
#             session['user_type'] = 'student'
#             session.permanent = True

#             id_card_front_b64 = create_dummy_image_base64("ID Card - Front", student['name'], student['id'])
#             id_card_back_b64 = create_dummy_image_base64("ID Card - Back (Terms)", student['name'], student['id'])

#             return jsonify({
#                 "status": "success",
#                 "user_type": "student",
#                 "user_data": student,
#                 "other_required_data": {"message": f"Welcome, {student['name']}!"},
#                 "id_images_base64": {"front": id_card_front_b64, "back": id_card_back_b64}
#             }), 200
#         else:
#             return jsonify({"error": "Student not found with provided credentials"}), 404


#     # --- LOGIN TEACHER ---
#     @app.route('/login/teacher', methods=['POST', 'OPTIONS'])
#     def login_teacher():
#         if request.method == 'OPTIONS':
#             return _build_cors_preflight_response()

#         data = request.get_json()
#         if not data:
#             return jsonify({"error": "Invalid input, JSON expected"}), 400

#         name = data.get('name')
#         email = data.get('email')
#         phone = data.get('phone')
#         teacher = teacher_at_db(name=name, email=email, phone=phone)

#         if teacher:
#             session['user_id'] = teacher['id']
#             session['user_type'] = 'teacher'

#             id_card_front_b64 = create_dummy_image_base64("ID Card - Front", teacher['name'], teacher['id'])
#             id_card_back_b64 = create_dummy_image_base64("ID Card - Back (Staff)", teacher['name'], teacher['id'])

#             return jsonify({
#                 "status": "success",
#                 "user_type": "teacher",
#                 "user_data": teacher,
#                 "other_required_data": {"message": f"Welcome, {teacher['name']}!"},
#                 "id_images_base64": {"front": id_card_front_b64, "back": id_card_back_b64}
#             }), 200
#         else:
#             return jsonify({"error": "Teacher not found with provided credentials"}), 404


#     # --- PROFILE ---
#     @app.route('/profile', methods=['GET'])
#     def get_profile():
#         if 'user_id' in session and 'user_type' in session:
#             user_id = session['user_id']
#             user_type = session['user_type']

#             user_data = student_at_db(user_id=user_id) if user_type == 'student' else teacher_at_db(user_id=user_id)

#             if user_data:
#                 return jsonify({
#                     "status": "success",
#                     "logged_in_as": user_type,
#                     "user_data": user_data
#                 }), 200
#             else:
#                 session.clear()
#                 return jsonify({"error": "User not found, session cleared"}), 404
#         else:
#             return jsonify({"error": "Unauthorized. Please log in first."}), 401


#     # --- LOGOUT ---
#     @app.route('/logout', methods=['POST'])
#     def logout():
#         session.clear()
#         return jsonify({"status": "success", "message": "You have been logged out."}), 200


#     # --- Helper for CORS preflight ---
#     def _build_cors_preflight_response():
#         response = make_response()
#         response.headers.add("Access-Control-Allow-Origin", "http://127.0.0.1:5000")
#         response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
#         response.headers.add("Access-Control-Allow-Methods", "POST,GET,OPTIONS")
#         response.headers.add("Access-Control-Allow-Credentials", "true")
#         return response



















# import uuid
# import time
# import random
# from flask import Flask, Blueprint, request, render_template_string, redirect, url_for, session

# # --- Configuration & Mock Data ---

# # In a real application, replace this with a proper database connection.
# # MOCK_DATABASE now holds both user info and temporary reset data
# MOCK_DATABASE = {
#     "user@example.com": {"id": 1, "password_hash": "mock_hashed_password_123", "reset_code": None, "code_expiry": 0, "session_key": None},
#     "student@flask.com": {"id": 2, "password_hash": "mock_hashed_password_456", "reset_code": None, "code_expiry": 0, "session_key": None}
# }

# CODE_EXPIRY_SECONDS = 300  # 5 minutes for the code

# # --- Utility Functions ---

# def send_verification_code(email, code):
#     """
#     Mocks sending an email/SMS with the 6-digit verification code.
#     In a real app, you would use a service like Twilio or SendGrid here.
#     """
#     print(f"\n--- MOCK EMAIL/SMS SENT ---\nTo: {email}")
#     print(f"Subject: Your Password Reset Code")
#     print(f"Code: {code}")
#     print(f"This code is valid for {CODE_EXPIRY_SECONDS} seconds.")
#     print("-------------------------\n")
#     return True

# def generate_and_store_code(email):
#     """Generates a 6-digit code and stores it with an expiry timestamp."""
#     user_data = MOCK_DATABASE.get(email)
#     if not user_data:
#         return None

#     # Generate a 6-digit numeric code
#     code = str(random.randint(100000, 999999))
#     expiry = time.time() + CODE_EXPIRY_SECONDS

#     # Store the code and its expiry directly with the user's data
#     user_data["reset_code"] = code
#     user_data["code_expiry"] = expiry
#     user_data["session_key"] = None # Clear any previous session key
#     return code

# def update_user_password(email, new_password):
#     """Mocks updating the user's password in the database."""
#     user_data = MOCK_DATABASE.get(email)
#     if user_data:
#         # In a real app, HASH the new_password here before saving!
#         user_data["password_hash"] = f"new_hashed_password_{new_password}" 
#         # Clear all reset data after successful update
#         user_data["reset_code"] = None
#         user_data["code_expiry"] = 0
#         user_data["session_key"] = None
#         print(f"\n*** Password for {email} successfully updated. ***\n")
#         return True
#     return False

# # --- Blueprint Definition ---

# student_bp = Blueprint('student', __name__, url_prefix='/student')

# @student_bp.route('/forgot-password', methods=['GET', 'POST'])
# def forgot_password():
#     """
#     Stage 1: Collects the user's email, generates a code, and sends it.
#     """
#     message = None
#     if request.method == 'POST':
#         email = request.form.get('email', '').strip().lower()
        
#         # 1. Check if email exists (security: always respond vaguely)
#         if email not in MOCK_DATABASE:
#             # Prevent enumeration attacks by responding generically
#             print(f"Attempted reset for non-existent email: {email}")
#             message = "If an account exists with that email, a verification code has been sent."
#             return render_template_string(FORGOT_PASSWORD_HTML, message=message, email="")
        
#         # 2. Generate and store code
#         code = generate_and_store_code(email)
        
#         # 3. Send email (mocked)
#         send_verification_code(email, code)
        
#         # 4. Redirect to the verification step, passing email via query or session
#         session['reset_email'] = email # Use Flask session for state management
        
#         return redirect(url_for('student.verify_code'))

#     return render_template_string(FORGOT_PASSWORD_HTML, message=message, email="")

# @student_bp.route('/verify-code', methods=['GET', 'POST'])
# def verify_code():
#     """
#     Stage 2: Accepts the 6-digit code and verifies it. If successful, issues a session key.
#     """
#     email = session.get('reset_email')
#     if not email or email not in MOCK_DATABASE:
#         return redirect(url_for('student.forgot_password'))

#     message = None
#     user_data = MOCK_DATABASE.get(email)

#     if request.method == 'POST':
#         user_code = request.form.get('code', '').strip()
        
#         # Check against stored code and expiry
#         if user_data["reset_code"] == user_code and user_data["code_expiry"] > time.time():
#             # Code is correct and valid. Issue a secure, one-time session key (UUID).
#             session_key = str(uuid.uuid4())
#             user_data["session_key"] = session_key
            
#             # Clear the short code and its expiry immediately to prevent reuse
#             user_data["reset_code"] = None
#             user_data["code_expiry"] = 0
            
#             # Redirect to the final reset form using the session key
#             return redirect(url_for('student.reset_password', session_key=session_key))
        
#         elif user_data["code_expiry"] <= time.time() and user_data["reset_code"]:
#             message = "Error: Code has expired. Please request a new code."
#             # Clear expired code
#             user_data["reset_code"] = None
#             user_data["code_expiry"] = 0
#         else:
#             message = "Error: Invalid verification code."

#     # If GET or POST with error
#     return render_template_string(VERIFY_CODE_HTML, email=email, message=message)


# @student_bp.route('/reset-password/<session_key>', methods=['GET', 'POST'])
# def reset_password(session_key):
#     """
#     Stage 3: Verifies the session key and updates the password.
#     """
#     # Find the user associated with this session key
#     user_email = next((e for e, data in MOCK_DATABASE.items() if data["session_key"] == session_key), None)
    
#     if not user_email:
#         # Invalid or expired session key
#         return f"<h1>Invalid or Expired Link</h1><p>The password reset link is invalid or has expired. Please restart the process.</p>", 400

#     user_data = MOCK_DATABASE.get(user_email)
#     message = None

#     if request.method == 'POST':
#         new_password = request.form.get('new_password')
#         confirm_password = request.form.get('confirm_password')
        
#         if new_password != confirm_password:
#             message = "Error: Passwords do not match."
#         elif len(new_password) < 8:
#             message = "Error: Password must be at least 8 characters long."
        
#         if message:
#             return render_template_string(RESET_PASSWORD_HTML, session_key=session_key, email=user_email, message=message)

#         # 4. Update the password
#         if update_user_password(user_email, new_password):
#             # The update_user_password function already clears the session_key
#             session.pop('reset_email', None) # Clear the session variable
#             return redirect(url_for('student.confirmation', type='reset'))

#         # Should not happen if logic is correct
#         return "An internal error occurred during password update.", 500

#     # GET request: Display the form to set a new password
#     return render_template_string(RESET_PASSWORD_HTML, session_key=session_key, email=user_email, message="")


# @student_bp.route('/confirmation')
# def confirmation():
#     """A generic confirmation page."""
#     type = request.args.get('type')
#     if type == 'reset':
#         message = "Password successfully reset! You can now log in with your new password."
#     else:
#         message = "Reset instructions sent! Please check your email inbox."
    
#     return f"""
#     <!doctype html>
#     <html lang="en">
#     <head>
#         <meta name="viewport" content="width=device-width, initial-scale=1.0">
#         <title>Confirmation</title>
#     </head>
#     <body style="font-family: sans-serif; padding: 20px; max-width: 400px; margin: auto;">
#         <h1>Success</h1>
#         <p style="color: green; font-weight: bold;">{message}</p>
#         <p><a href="/">Return to Home</a> | <a href="{url_for('student.forgot_password')}">Request Another Reset</a></p>
#     </body>
#     </html>
#     """

# # --- Flask App Setup ---

# app = Flask(__name__)
# # IMPORTANT: A secret key is required to use Flask sessions.
# app.config['SECRET_KEY'] = 'a-very-secure-random-string-for-session-management' 
# app.register_blueprint(student_bp)

# # Dummy root route for testing context
# @app.route('/')
# def home():
#     return f"""
#     <body style="font-family: sans-serif; padding: 20px; max-width: 400px; margin: auto;">
#     <h1>Flask Forgot Password Demo (Verification Code)</h1>
#     <p>Use the test email: <strong>student@flask.com</strong></p>
#     <p>Visit the <a href="{url_for('student.forgot_password')}">Forgot Password Page</a> to start the flow.</p>
#     </body>
#     """


# # --- HTML TEMPLATES (Minimal, embedded for single-file execution) ---

# FORGOT_PASSWORD_HTML = """
# <!doctype html>
# <html lang="en">
# <head>
#     <meta name="viewport" content="width=device-width, initial-scale=1.0">
#     <title>Forgot Password</title>
# </head>
# <body style="font-family: sans-serif; padding: 20px; max-width: 400px; margin: auto; background-color: #f4f4f9;">
#     <div style="background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
#         <h1 style="color: #333;">Forgot Password</h1>
#         <p style="color: #666;">Enter your email address to receive a 6-digit verification code.</p>
#         {% if message %}
#             <p style="color: green; font-weight: bold; padding: 10px; border: 1px solid #d4edda; background-color: #f6fff6; border-radius: 4px;">{{ message }}</p>
#         {% endif %}
#         <form method="POST">
#             <label for="email" style="display: block; margin-bottom: 5px; font-weight: bold;">Email Address:</label>
#             <input type="email" id="email" name="email" required 
#                    style="width: 100%; padding: 10px; margin-top: 5px; margin-bottom: 20px; border: 1px solid #ccc; border-radius: 4px;"
#                    placeholder="e.g., student@flask.com">
#             <button type="submit" 
#                     style="width: 100%; background-color: #007bff; color: white; padding: 12px 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; transition: background-color 0.3s;">
#                 Send Code
#             </button>
#         </form>
#     </div>
# </body>
# </html>
# """

# VERIFY_CODE_HTML = """
# <!doctype html>
# <html lang="en">
# <head>
#     <meta name="viewport" content="width=device-width, initial-scale=1.0">
#     <title>Verify Code</title>
# </head>
# <body style="font-family: sans-serif; padding: 20px; max-width: 400px; margin: auto; background-color: #f4f4f9;">
#     <div style="background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
#         <h1 style="color: #333;">Verify Code</h1>
#         <p style="color: #666;">A 6-digit code has been sent to <strong>{{ email }}</strong>. It expires in 5 minutes.</p>
#         {% if message %}
#             <p style="color: red; font-weight: bold; padding: 10px; border: 1px solid #f5c6cb; background-color: #f8d7da; border-radius: 4px;">{{ message }}</p>
#         {% endif %}
#         <form method="POST">
#             <label for="code" style="display: block; margin-bottom: 5px; font-weight: bold;">Verification Code:</label>
#             <input type="text" id="code" name="code" required maxlength="6" pattern="\d{6}"
#                    style="width: 100%; padding: 10px; margin-top: 5px; margin-bottom: 20px; border: 1px solid #ccc; border-radius: 4px; text-align: center; font-size: 20px;"
#                    placeholder="123456">
            
#             <button type="submit" 
#                     style="width: 100%; background-color: #007bff; color: white; padding: 12px 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; margin-bottom: 10px;">
#                 Verify Code
#             </button>
#             <p style="text-align: center;"><a href="{{ url_for('student.forgot_password') }}" style="color: #007bff; text-decoration: none; font-size: small;">Resend Code</a></p>
#         </form>
#     </div>
# </body>
# </html>
# """

# RESET_PASSWORD_HTML = """
# <!doctype html>
# <html lang="en">
# <head>
#     <meta name="viewport" content="width=device-width, initial-scale=1.0">
#     <title>Reset Password</title>
# </head>
# <body style="font-family: sans-serif; padding: 20px; max-width: 400px; margin: auto; background-color: #f4f4f9;">
#     <div style="background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
#         <h1 style="color: #333;">Set New Password</h1>
#         <p style="color: #666;">For account: <strong>{{ email }}</strong></p>
#         {% if message %}
#             <p style="color: red; font-weight: bold; padding: 10px; border: 1px solid #f5c6cb; background-color: #f8d7da; border-radius: 4px;">{{ message }}</p>
#         {% endif %}
#         <form method="POST">
#             <input type="hidden" name="session_key" value="{{ session_key }}">
            
#             <label for="new_password" style="display: block; margin-bottom: 5px; font-weight: bold;">New Password (min 8 chars):</label>
#             <input type="password" id="new_password" name="new_password" required 
#                    style="width: 100%; padding: 10px; margin-top: 5px; margin-bottom: 20px; border: 1px solid #ccc; border-radius: 4px;"><br>
            
#             <label for="confirm_password" style="display: block; margin-bottom: 5px; font-weight: bold;">Confirm New Password:</label>
#             <input type="password" id="confirm_password" name="confirm_password" required 
#                    style="width: 100%; padding: 10px; margin-top: 5px; margin-bottom: 20px; border: 1px solid #ccc; border-radius: 4px;">
            
#             <button type="submit" 
#                     style="width: 100%; background-color: #28a745; color: white; padding: 12px 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px;">
#                 Update Password
#             </button>
#         </form>
#     </div>
# </body>
# </html>
# """

# if __name__ == '__main__':
#     # Use 'student@flask.com' to test the successful path
#     print("MOCK DB User: student@flask.com")
#     # For this self-contained script, we use app.run()
#     app.run(debug=True)
