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

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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
        
        svg_path_1 = "tmp/student_id_card_front.svg"
        svg_path_2 = "tmp/student_id_card_back.svg"
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
    qr_code_url = "/tmp/qrcode.png"

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
        "front_svg_path": "/tmp/student_id_card_front.svg",
        "back_svg_path": "/tmp/student_id_card_back.svg"
    }



# --- Helper for CORS preflight ---
def _build_cors_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "http://127.0.0.1:5000")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "POST,GET,OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response








 