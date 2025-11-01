from flask import Blueprint ,jsonify,  make_response,request,session
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
from utils.card import merge_svg_template_back, merge_svg_template_front_teacher
from db_connection import get_collection
from utils.email_service import send_email
from utils.upload_to_cloudiary import upload_file


teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')

load_dotenv()  # Loads variables from .env into os.environ

JWT_SECRET = os.getenv("JWT_SECRET")


@teacher_bp.route('/login' ,methods=['POST'])
def teacher_login():


    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()

    print("finl")

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input, JSON expected"}), 400
 
    print(data)

    try:
        name =data.get('name','')
        email =data.get('email','')
        phone =data.get('phone','')
        password =data.get('password','')

        print(name,email,phone,password,"dam")

        # Validate input
        if not name:
            return jsonify({"error": "Please provide name."}), 400
        elif not (email or phone):
            return jsonify({"error": "Please provide either an email or a phone number."}), 400

        # Get collection
        teacher_collection = get_collection('teacher')

        # Build query
        query = { "name": { "$regex": f"^{name}$", "$options": "i" } }
        # query = {}
        if email:
            query['email'] = email
        elif phone:
            query['phone'] = int(phone)


        teacher = teacher_collection.find_one(query)

        if not teacher:
            return jsonify({"message": "Teacher not found"}), 404

        # Convert ObjectId to string
        teacher['_id'] = str(teacher['_id'])

        print(teacher["password"])


        if not check_password_hash(teacher['password'], password): 
            return jsonify({"error": "Invalid password"}), 401


        # for admin only section start

        if teacher['role'] == 'admin' :
            return jsonify({"message": "Admin logged in." , "user_id" : teacher['_id'] , "type" : "admin"})

        # for admin only section end 

          
        if teacher['profile'].strip() =='' or teacher['sign'].strip() == '' :
            return jsonify({"message": "No profile or sign found " , "user_id" : teacher['_id'] , "type" : "teacher"}), 400


        session['user_id'] = teacher['_id']
        session['user_type'] = 'teacher'
        session.permanent = True

        # making card
        make_card(teacher)
        
        svg_path_1 = "../tmp/teacher_id_card_front.svg"
        svg_path_2 = "../tmp/teacher_id_card_back.svg"

        # Read SVG files and encode in base64 (so they can be sent via JSON)
        def encode_svg(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")

        svg1 = encode_svg(svg_path_1)
        svg2 = encode_svg(svg_path_2)

        response = {
        "svg_files": {
            "front.svg": svg1,
            "back.svg": svg2
        },
        "message": "Teacher fetched successfully",
        "type" : "teacher"
        }

        return jsonify(response) ,200


    except Exception as e:
        return jsonify({"error": str(e)}), 500


#     # --- LOGOUT ---
@teacher_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"status": "success", "message": "You have been logged out."}), 200



 
@teacher_bp.route('/update', methods=['POST'])
def update_teacher():

 

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
        teacher_collection = get_collection('teacher')

    
        teacher =  teacher_collection.find_one({'_id': obj_id})

        print(teacher)
        if not teacher:
            return jsonify({"message": "Teacher not found"}), 404

        

        update_fields = {}
        teacher['_id'] = str(teacher['_id'])
 
        # Upload photo if provided
        photo_url = "" 
        sign_url= ""

        if 'photo' in files:
            photo_file = files['photo']
            photo_resp = upload_file(photo_file, 'teacher')
            photo_url = photo_resp.get("secure_url")
            update_fields['profile'] = photo_url

        # Upload sign if provided
        if 'sign' in files:
            sign_file = files['sign']
            sign_resp = upload_file(sign_file, 'teacher',remove_bg=True)
            sign_url = sign_resp.get("secure_url")
            update_fields['sign'] = sign_url

        # Perform update in database
        if update_fields:
            teacher_collection.update_one({'_id': ObjectId(teacher['_id'])}, {'$set': update_fields})
        
        print(teacher)

        teacher["sign"] = sign_url
        teacher["profile"] = photo_url

        print(teacher)
        make_card(teacher)
        
        svg_path_1 = "../tmp/teacher_id_card_front.svg"
        svg_path_2 = "../tmp/teacher_id_card_back.svg"
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
        "message": "Teacher fetched successfully",
        }

     

        return jsonify(response) ,200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

 



@teacher_bp.route('/get', methods=['GET'])
def get_teacher_credential():
    try:

        name =  request.args.get('name')
        email = request.args.get('email')
        phone = request.args.get('phone')


        # Validate input
        if not name:
            return jsonify({"error": "Please provide name."}), 400
        elif not (email or phone):
            return jsonify({"error": "Please provide either an email or a phone number."}), 400

        # Get collection
        teacher_collection = get_collection('teacher')

        # Build query
        query = { "name": { "$regex": f"^{name}$", "$options": "i" } }
        # query = {}
        if email:
            query['email'] = email
        elif phone:
            query['phone'] = int(phone)


        teacher = teacher_collection.find_one(query)

        if not teacher:
            return jsonify({"message": "Teacher not found"}), 404

        # Convert ObjectId to string


        teacher['_id'] = str(teacher['_id'])

        password = generate_password(8)


        hashed_password = generate_password_hash(password)

    
        # Update the password in the database
        result = teacher_collection.update_one(
            {"_id": ObjectId(teacher["_id"])},  # Filter by student ID
            {"$set": {"password": hashed_password}}
        )

      

        email_body = f""" 

        Dear {teacher["name"]},

        We hope you are doing well. Please find below your login credentials for accessing the student portal. Kindly keep this information confidential and do not share it with anyone.

        Student Details:

        Name: {teacher["name"]}

        Phone No: {teacher["phone"]}

        Email ID: {teacher["email"]}

        Password: {password}

        You can use these credentials to log in at 
        https://5173-firebase-id-1760600822304.cluster-m7dwy2bmizezqukxkuxd55k5ka.cloudworkstations.dev/login.

        If you face any issues while logging in or need to reset your password, please contact the support team.

        Best regards,
        Digital Student ID Card Team

        """

       

        send_email("Digital ID Card - Teacher Login Credentials",email_body,teacher["email"])

        return jsonify({
            "message": f"""Credentials is sent to {teacher["email"]} successfully""",
        
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


 

def make_card(teacher_data):
 
    with open('other/college.json', 'r') as file:
        college_data = json.load(file)  # Load JSON data into a Python dictionary

  
    make_qr_code({
       "name" : teacher_data["name"],
       "email" : teacher_data["email"],
       "phone" : teacher_data["phone"],
       "type" : "teacher"
    })
    qr_code_url = "tmp/qrcode.png"

    merge_svg_template_front_teacher({
        "name": teacher_data["name"],
        "phone": str(teacher_data["phone"]),
        "dob": str(teacher_data["dob"]),
        "address" : teacher_data["address"],
        "profile_url" : teacher_data["profile"],
        "teacher_sign_url" : teacher_data["sign"],
        "qualification" : teacher_data["qualification"],
        "designation" : teacher_data["designation"],

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

        "student_contact" :str( teacher_data["phone"]),
        "date_issued" : str(teacher_data["issue_date"])[:10],
        "qr_code_url" : qr_code_url 
    }, OUTPUT_PATH="../tmp/teacher_id_card_back.svg")

    return {
        "message": "Card generated successfully",
        "front_svg_path": "tmp/teacher_id_card_front.svg",
        "back_svg_path": "tmp/teacher_id_card_back.svg"
    }



# --- Helper for CORS preflight ---
def _build_cors_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "http://127.0.0.1:5000")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "POST,GET,OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response




def generate_password(length=8):
    # Define the characters to choose from: only letters and digits
    characters = string.ascii_letters + string.digits
    # Randomly select `length` characters
    password = ''.join(random.choice(characters) for _ in range(length))
    return password
