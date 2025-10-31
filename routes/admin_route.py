from flask import Blueprint , request, jsonify
from bson import ObjectId
from pymongo import MongoClient
import os
import sys
from datetime import datetime
from bson.objectid import ObjectId
from bson.errors import InvalidId
from werkzeug.utils import secure_filename


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.upload_to_cloudiary import upload_file
from db_connection import get_collection
from utils.upload_to_dropbox import  get_dropbox_client , upload_file as upload_file_dropbox
from utils.excel_operation import excel_to_dict




admin_bp = Blueprint('admin', __name__, url_prefix='/admin')



# 

@admin_bp.route('/dashboard')
def dashboard():
    return "Admin Dashboard"


 
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@admin_bp.route('/design/id', methods=['POST'])
def design_id_card():
    try:
        # Get JSON-like fields from form
        # If client sends a JSON blob in a field called "payload", parse it:
        payload = {}
        if 'payload' in request.form:
            # client might have appended a JSON string under 'payload'
            import json
            try:
                payload = json.loads(request.form['payload'])
            except Exception:
                payload = {}
        else:
            # or individual form fields:
            payload = request.form.to_dict()

        # Files
        sign_file = request.files.get('sign')   # <input name="sign" type="file" />
        logo_file = request.files.get('logo')   # <input name="logo" type="file" />

        # Validate presence (customize as needed)
        if sign_file is None or logo_file is None:
            return jsonify({"error": "Both 'sign' and 'logo' files are required."}), 400

        if not (allowed_file(sign_file.filename) and allowed_file(logo_file.filename)):
            return jsonify({"error": "Invalid file type. Allowed: png,jpg,jpeg,gif"}), 400

        print(payload)


        # Upload to Cloudinary
        # Optionally you can set folder/public_id based on payload (e.g., student id)
        folder = "id_card_design"

        sign_upload_resp = upload_file(sign_file, folder=folder)
        logo_upload_resp = upload_file(logo_file, folder=folder)

        # print(sign_upload_resp)
        # Extract URLs or public_ids as required
        sign_url = sign_upload_resp.get("secure_url")
        # sign_public_id = sign_upload_resp.get("public_id")

        # print(sign_url)
        logo_url = logo_upload_resp.get("secure_url")
        # logo_public_id = logo_upload_resp.get("public_id")

        # sign_url=""
        # logo_url=""

        # Build the document to insert
        doc = {
            "primary_color" : payload.get("primary_color"),
            "college_name" : payload.get("college_name"),
            "address" : payload.get("address"),
            "phone" : payload.get("phone"),
            "sign_url":   sign_url,
            "logo_url": logo_url
        }

        # Insert into MongoDB
        print("before collection")

        college_collection = get_collection('id_card_design')
        print("after collection")
        result = college_collection.insert_one(doc)

        return jsonify({
            "message": "Design saved",
            "sign_url": sign_url,
            "logo_url": logo_url
        }), 201

    except Exception as e:
        # log error in production
        return jsonify({"error": str(e)}), 500



# student section 


@admin_bp.route('/add/student', methods=['POST'])
def add_student():
    try:
        # Get JSON-like fields from form
        # If client sends a JSON blob in a field called "payload", parse it:
        payload = {}
        if 'payload' in request.form:
            # client might have appended a JSON string under 'payload'
            import json
            try:
                payload = json.loads(request.form['payload'])
            except Exception:
                payload = {}
        else:
            # or individual form fields:
            payload = request.form.to_dict()

        print(payload)

        # Files
        profile = request.files.get('profile')   # <input name="sign" type="file" />
        profile_url = ""
        # # Validate presence (customize as needed)
        if profile  :
            profile_resp = upload_file(profile, folder="student")
            profile_url = profile_resp.get("secure_url")
             


        year_map = {
            "1st": 1,
            "2nd": 2,
            "3rd": 3,
            "Final": 4  # assuming 'Final year' means 4th year
        }
                
        parts = payload.get("class").split()
        course = parts[0]  # e.g., "B.Tech"
        year_word = parts[1]  # e.g., "2nd", "1st", "3rd"
        year_num = year_map.get(year_word, None)
        print(year_num)

        # Build the document to insert
        doc = {
            "name": payload.get("name"),
            "registration_no": payload.get("registration_no",""),
            "email": payload.get("email"),
            "phone": payload.get("phone"),
            "father_name": payload.get("father_name"),
            "address": payload.get("address"),
            "class": course,  # changed from college_name
            "year" : year_num,
            "valid_session": payload.get("valid_session"),
            "roll_no": int(payload.get("roll_no")),
            "dob": datetime.strptime(payload.get('dob'), "%Y-%m-%d"),
            "profile": profile_url,
            "sign" : "",
            "issue_date": datetime.now() 
        }

        # "issue date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Insert into MongoDB
        # print("before collection")

        college_collection = get_collection('student')
        # print("after collection")
        result = college_collection.insert_one(doc)

        # print(doc)
        return jsonify({
            "message": "Add successfully",

        }), 201

    except Exception as e:
        # log error in production
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/delete/student/<id>', methods=['DELETE'])
def delete_student(id):
    try:
        # Get the collection
        college_collection = get_collection('student')
        
        # Attempt to delete by ObjectId
        result = college_collection.delete_one({'_id': ObjectId(id)})

        if result.deleted_count == 0:
            return jsonify({"message": "Student not found"}), 404

        return jsonify({"message": "Student deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


 
@admin_bp.route('/update/student/<id>', methods=['PUT'])
def update_student(id):
    try:
        # Validate ObjectId
        try:
            obj_id = ObjectId(id)
        except InvalidId:
            return jsonify({"error": "Invalid student ID"}), 400

        # Get collection
        student_collection = get_collection('student')

        # Fetch existing student
        existing_teacher = student_collection.find_one({"_id": obj_id})
        if not existing_teacher:
            return jsonify({"error": "Student not found"}), 404

        # Parse form data
        payload = {}
        if 'payload' in request.form:
            import json
            try:
                payload = json.loads(request.form['payload'])
            except Exception:
                payload = {}
        else:
            payload = request.form.to_dict()

        # Handle file (profile image)
        profile = request.files.get('profile')
        profile_url = existing_teacher.get("profile")  # Default to old value

        if profile:
            profile_resp = upload_file(profile, folder="student")
            profile_url = profile_resp.get("secure_url")

        # Fields to possibly update
        update_fields = {
            "name": payload.get("name", existing_teacher.get("name")),
            "registration_no": payload.get("registration_no", existing_teacher.get("registration_no")),
            "email": payload.get("email", existing_teacher.get("email")),
            "phone": payload.get("phone", existing_teacher.get("phone")),
            "father_name": payload.get("father_name", existing_teacher.get("father_name")),
            "address": payload.get("address", existing_teacher.get("address")),
            "class": payload.get("class", existing_teacher.get("class")),
            "valid_session": payload.get("valid_session", existing_teacher.get("valid_session")),
            "roll_no": payload.get("roll_no", existing_teacher.get("roll_no")),
            "dob": payload.get("dob", existing_teacher.get("dob")),
            "profile": profile_url,
            "issue date": existing_teacher.get("issue date")  # Keep old issue date
        }

        # Update in DB
        result = student_collection.update_one({"_id": obj_id}, {"$set": update_fields})

        return jsonify({"message": "Student updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@admin_bp.route('/get/student', methods=['GET'])
def get_student():
    try:
        roll_no = int( request.args.get('roll_no'))
        registration_no = request.args.get('registration_no')

        # Validate input
        if not roll_no and not registration_no:
            return jsonify({"error": "Please provide either roll_no or registration_no"}), 400

        # Get collection
        student_collection = get_collection('student')

        # Build query
        query = {}
        if roll_no:
            query['roll_no'] = roll_no
        elif registration_no:
            query['registration_no'] = registration_no

        # Fetch student
        student = student_collection.find_one(query)

        if not student:
            return jsonify({"message": "Student not found"}), 404

        # Convert ObjectId to string
        student['_id'] = str(student['_id'])

        return jsonify({
            "message": "Student fetched successfully",
            "data": student
        }), 200


    except Exception as e:
        return jsonify({"error": str(e)}), 500



# students section


@admin_bp.route('/add/students', methods=['POST'])
def add_students():
    try:
        # Get JSON-like fields from form
        # If client sends a JSON blob in a field called "payload", parse it:
        payload = {}
        if 'payload' in request.form:
            # client might have appended a JSON string under 'payload'
            import json
            try:
                payload = json.loads(request.form['payload'])
            except Exception:
                payload = {}
        else:
            # or individual form fields:
            payload = request.form.to_dict()

        # Files
        excel_file = request.files.get('excel_file')   # <input name="sign" type="file" />
        dropbox_path = "/ID_card/file.txt"
        students_data = []


        # # Validate presence (customize as needed)
        if excel_file  :
            filename = secure_filename(excel_file.filename)
            temp_path = os.path.join('/tmp', filename)  # Use /tmp or another temp folder

            # Save file temporarily
            excel_file.save(temp_path)

            # Define Dropbox path (e.g., /uploads/filename.ext)
            dropbox_path = f"/ID_card/add-{filename}"

            dbx = get_dropbox_client()
    
            # 2. Check if initialization was successful
            if dbx is None:
                print("Failed to initialize Dropbox client. Exiting.")
                return # Exit the script

            # 3. Attempt to upload the file
            # print(f"2. Attempting to upload '{LOCAL_UPLOAD_FILENAME}' to '{DROPBOX_FILE_PATH}'...")
            success = upload_file_dropbox(dbx, temp_path, dropbox_path)
    

            # Upload to Dropbox
            # success = upload_file_dropbox(temp_path, dropbox_path)

            start_row = int(payload.get("start_row_no",0))
            end_row = int(payload.get("end_row_no"))

            print(start_row,end_row)

            students_data = excel_to_dict(temp_path,start_row=start_row , end_row=end_row)

            

            year_map = {
                "1st": 1,
                "2nd": 2,
                "3rd": 3,
                "Final": 4  # assuming 'Final year' means 4th year
            }
                    
          

            for st in students_data :
                st["issue_date"] = datetime.now()
                st["profile"] = ""
                st["sign"] = ""
                st["roll_no"] = int(st["roll_no"])
                if not st.get("registration_no"):
                    st["registration_no"] = ""
                
                parts = st['class'].split()
                course = parts[0]  # e.g., "B.Tech"
                year_word = parts[1]  # e.g., "2nd", "1st", "3rd"
                year_num = year_map.get(year_word, None)
                print(year_num)
                st["class"] = course
                st["year"] = year_num
                st["dob"] = datetime.strptime( st["dob"], "%Y-%m-%d"),



            if success : 
                file_collection = get_collection('file')
                # print("after collection")
                result = file_collection.insert_one({ "type" : "student" ,"file_type" : "excel" ,  "operation" : "add", "path" : dropbox_path, "timestamp" : datetime.now() })
                    # Optionally delete local temp file after upload

            os.remove(temp_path)


        print(students_data)
        
 

        student_collection = get_collection('student')
        # print("after collection")
        result = student_collection.insert_many(students_data)

        # print(doc)
        return jsonify({
            "message": f"Add {len(students_data)} students successfully",

        }), 201

    except Exception as e:
        # log error in production
        return jsonify({"error": str(e)}), 500




@admin_bp.route('/delete/students', methods=['DELETE'])
def delete_students():
    try:
        # Get JSON-like fields from form
        # If client sends a JSON blob in a field called "payload", parse it:
        payload = {}
        if 'payload' in request.form:
            # client might have appended a JSON string under 'payload'
            import json
            try:
                payload = json.loads(request.form['payload'])
            except Exception:
                payload = {}
        else:
            # or individual form fields:
            payload = request.form.to_dict()

        # Files
        excel_file = request.files.get('excel_file')   # <input name="sign" type="file" />
        dropbox_path = "/ID_card/file.txt"
        students_data = []


        # # Validate presence (customize as needed)
        if excel_file  :
            filename = secure_filename(excel_file.filename)
            temp_path = os.path.join('/tmp', filename)  # Use /tmp or another temp folder

            # Save file temporarily
            excel_file.save(temp_path)

            # Define Dropbox path (e.g., /uploads/filename.ext)
            dropbox_path = f"/ID_card/delete-{filename}"

            dbx = get_dropbox_client()
    
            # 2. Check if initialization was successful
            if dbx is None:
                print("Failed to initialize Dropbox client. Exiting.")
                return # Exit the script

            # 3. Attempt to upload the file
            # print(f"2. Attempting to upload '{LOCAL_UPLOAD_FILENAME}' to '{DROPBOX_FILE_PATH}'...")
            success = upload_file_dropbox(dbx, temp_path, dropbox_path)
    

            # Upload to Dropbox
            # success = upload_file_dropbox(temp_path, dropbox_path)

            start_row = int(payload.get("start_row_no",0))
            end_row = int(payload.get("end_row_no"))

            print(start_row,end_row)

            students_data = excel_to_dict(temp_path,start_row=start_row , end_row=end_row)
            student_roll_no = []
            deleted_student_count = 0

            for st in students_data :
                student_roll_no.append(int(st["roll_no"]))
                

            if success : 
                file_collection = get_collection('file')
                # print("after collection")
                result = file_collection.insert_one({ "type" : "student" ,"file_type" : "excel" , "operation" : "delete", "path" : dropbox_path , "timestamp" : datetime.now() })

                

                # Perform deletion
                student_collection = get_collection('student')
                result = student_collection.delete_many({ "roll_no": { "$in": student_roll_no } })
                deleted_student_count = result.deleted_count
                print(f"Deleted {result.deleted_count} documents.")


            os.remove(temp_path)

        
  
        # print(doc)
        return jsonify({
            "message": f"Drop {deleted_student_count} students successfully",

        }), 201

    except Exception as e:
        # log error in production
        return jsonify({"error": str(e)}), 500




@admin_bp.route('/update/students', methods=['PUT'])
def update_students():
    try:
        # Get JSON-like fields from form
        # If client sends a JSON blob in a field called "payload", parse it:
        payload = {}
        if 'payload' in request.form:
            # client might have appended a JSON string under 'payload'
            import json
            try:
                payload = json.loads(request.form['payload'])
            except Exception:
                payload = {}
        else:
            # or individual form fields:
            payload = request.form.to_dict()

        # Files
        excel_file = request.files.get('excel_file')   # <input name="sign" type="file" />
        dropbox_path = "/ID_card/file.txt"
        students_data = []


        # # Validate presence (customize as needed)
        if excel_file  :
            filename = secure_filename(excel_file.filename)
            temp_path = os.path.join('/tmp', filename)  # Use /tmp or another temp folder

            # Save file temporarily
            excel_file.save(temp_path)

            # Define Dropbox path (e.g., /uploads/filename.ext)
            dropbox_path = f"/ID_card/update-{filename}"

            dbx = get_dropbox_client()
    
            # 2. Check if initialization was successful
            if dbx is None:
                print("Failed to initialize Dropbox client. Exiting.")
                return # Exit the script

            # 3. Attempt to upload the file
            # print(f"2. Attempting to upload '{LOCAL_UPLOAD_FILENAME}' to '{DROPBOX_FILE_PATH}'...")
            success = upload_file_dropbox(dbx, temp_path, dropbox_path)
    

            # Upload to Dropbox
            # success = upload_file_dropbox(temp_path, dropbox_path)

            start_row = int(payload.get("start_row_no",0))
            end_row = int(payload.get("end_row_no"))

            print(start_row,end_row)

            students_data = excel_to_dict(temp_path,start_row=start_row , end_row=end_row)
            student_roll_no = []
            updated_student_count = 0

            for st in students_data :
                student_roll_no.append(int(st["roll_no"]))
                

            if success : 
                file_collection = get_collection('file')
                # print("after collection")
                result = file_collection.insert_one({ "type" : "student" ,"file_type" : "excel" , "operation" : "update", "path" : dropbox_path , "timestamp" : datetime.now() })

                

                # Perform deletion
                student_collection = get_collection('student')
                result = student_collection.update_many(
                    { "roll_no": { "$in": student_roll_no } },   # filter condition
                    { "$inc": { "year": 1 } }  # update operation
                )
                updated_student_count = result.matched_count


            os.remove(temp_path)

        
  
        # print(doc)
        return jsonify({
            "message": f"Promote {updated_student_count} students successfully",

        }), 201

    except Exception as e:
        # log error in production
        return jsonify({"error": str(e)}), 500






# teacher section 



@admin_bp.route('/add/teacher', methods=['POST'])
def add_teacher():
    try:
        # Get JSON-like fields from form
        # If client sends a JSON blob in a field called "payload", parse it:
        payload = {}
        if 'payload' in request.form:
            # client might have appended a JSON string under 'payload'
            import json
            try:
                payload = json.loads(request.form['payload'])
            except Exception:
                payload = {}
        else:
            # or individual form fields:
            payload = request.form.to_dict()

        # Files
        profile = request.files.get('profile')   # <input name="sign" type="file" />
        profile_url = ""
        sign_url = ""
        # # Validate presence (customize as needed)
        if profile  :
            profile_resp = upload_file(profile, folder="teacher")
            profile_url = profile_resp.get("secure_url")
             
      
        # Build the document to insert
        doc = {
            "name": payload.get("name"),
            "email": payload.get("email"),
            "phone":int( payload.get("phone")),
            "address": payload.get("address"),
            "dob": datetime.strptime(payload.get('dob'), "%Y-%m-%d"),
            "qualification" : payload.get("qualification"),
            "designation" : payload.get("designation"),
            "profile": profile_url,
            "role" : payload.get("role","teacher"),
            "sign" : sign_url,
            "issue date": datetime.now() 
        }
 

        college_collection = get_collection('teacher')
        # print("after collection")
        result = college_collection.insert_one(doc)

        # print(doc)
        return jsonify({
            "message": "Add successfully",

        }), 201

    except Exception as e:
        # log error in production
        return jsonify({"error": str(e)}), 500



@admin_bp.route('/delete/teacher/<id>', methods=['DELETE'])
def delete_teacher(id):
    try:
        # Get the collection
        teacher_collection = get_collection('teacher')
        
        # Attempt to delete by ObjectId
        result = teacher_collection.delete_one({'_id': ObjectId(id)})

        if result.deleted_count == 0:
            return jsonify({"message": "Teacher not found"}), 404

        return jsonify({"message": "Teacher deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@admin_bp.route('/update/teacher/<id>', methods=['PUT'])
def update_teacher(id):
    try:
        # Validate ObjectId
        try:
            obj_id = ObjectId(id)
        except InvalidId:
            return jsonify({"error": "Invalid teacher ID"}), 400

        # Get collection
        teacher_collection = get_collection('teacher')

        # Fetch existing student
        existing_teacher = teacher_collection.find_one({"_id": obj_id})
        if not existing_teacher:
            return jsonify({"error": "Teacher not found"}), 404

       

        # Parse form data
        payload = {}
        if 'payload' in request.form:
            import json
            try:
                payload = json.loads(request.form['payload'])
            except Exception:
                payload = {}
        else:
            payload = request.form.to_dict()

        print(payload,existing_teacher)
        # return jsonify({"message": "Teacher updated successfully"}), 200

        # Handle file (profile image)
        profile = request.files.get('profile')
        profile_url = existing_teacher.get("profile")  # Default to old value

        if profile:
            profile_resp = upload_file(profile, folder="student")
            profile_url = profile_resp.get("secure_url")

        phone = payload.get("phone", existing_teacher.get("phone"))
        # Fields to possibly update
        update_fields = {
            "name": payload.get("name", existing_teacher.get("name")),
            "email": payload.get("email", existing_teacher.get("email")),
            "phone": int(phone) ,
            "address": payload.get("address", existing_teacher.get("address")),
            "dob": payload.get("dob", existing_teacher.get("dob")),
            "profile": profile_url,
            "qualification" : payload.get("qualification" , existing_teacher.get("qualification")),
            "designation" : payload.get("designation" , existing_teacher.get("designation")),
            "role" : payload.get("role", existing_teacher.get("role")),
            "sign" : payload.get("sign",existing_teacher.get("sign")),
            "issue date": existing_teacher.get("issue date"),  # Keep old issue date
        }

        # Update in DB
        result = teacher_collection.update_one({"_id": obj_id}, {"$set": update_fields})

        return jsonify({"message": "Teacher updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500





@admin_bp.route('/get/teacher', methods=['GET'])
def get_teacher():
    try:
        name =  request.args.get('name')
        email = request.args.get('email')
        phone = request.args.get('phone')

        print(email ,phone)

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

        return jsonify({
            "message": "Teacher fetched successfully",
            "data": teacher
        }), 200


    except Exception as e:
        return jsonify({"error": str(e)}), 500


# teachers section


@admin_bp.route('/add/teachers', methods=['POST'])
def add_teachers():
    try:
        # Get JSON-like fields from form
        # If client sends a JSON blob in a field called "payload", parse it:
        payload = {}
        if 'payload' in request.form:
            # client might have appended a JSON string under 'payload'
            import json
            try:
                payload = json.loads(request.form['payload'])
            except Exception:
                payload = {}
        else:
            # or individual form fields:
            payload = request.form.to_dict()

        # Files
        excel_file = request.files.get('excel_file')   # <input name="sign" type="file" />
        dropbox_path = "/ID_card/file.txt"
        teachers_data = []


        # # Validate presence (customize as needed)
        if excel_file  :
            filename = secure_filename(excel_file.filename)
            temp_path = os.path.join('/tmp', filename)  # Use /tmp or another temp folder

            # Save file temporarily
            excel_file.save(temp_path)

            # Define Dropbox path (e.g., /uploads/filename.ext)
            dropbox_path = f"/ID_card/add-{filename}"

            dbx = get_dropbox_client()
    
            # 2. Check if initialization was successful
            if dbx is None:
                print("Failed to initialize Dropbox client. Exiting.")
                return # Exit the script

            # 3. Attempt to upload the file
            # print(f"2. Attempting to upload '{LOCAL_UPLOAD_FILENAME}' to '{DROPBOX_FILE_PATH}'...")
            success = upload_file_dropbox(dbx, temp_path, dropbox_path)
    

            # Upload to Dropbox
            # success = upload_file_dropbox(temp_path, dropbox_path)

            start_row = int(payload.get("start_row_no",0))
            end_row = int(payload.get("end_row_no"))

            print(start_row,end_row)

            teachers_data = excel_to_dict(temp_path,start_row=start_row , end_row=end_row)      

            for te in teachers_data :
                te["issue_date"] = datetime.now()
                te["profile"] = ""
                te["sign"] = ""


            if success : 
                file_collection = get_collection('file')
                # print("after collection")
                result = file_collection.insert_one({ "type" : "teacher" ,"file_type" : "excel" ,  "operation" : "add", "path" : dropbox_path, "timestamp" : datetime.now() })
                    # Optionally delete local temp file after upload

            os.remove(temp_path)


        print(teachers_data)
        
 

        teacher_collection = get_collection('teacher')
        # print("after collection")
        result = teacher_collection.insert_many(teachers_data)

        # print(doc)
        return jsonify({
            "message": f"Add {len(teachers_data)} teacher successfully",

        }), 201

    except Exception as e:
        # log error in production
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/delete/teachers', methods=['DELETE'])
def delete_teachers():
    try:
        # Get JSON-like fields from form
        # If client sends a JSON blob in a field called "payload", parse it:
        payload = {}
        if 'payload' in request.form:
            # client might have appended a JSON string under 'payload'
            import json
            try:
                payload = json.loads(request.form['payload'])
            except Exception:
                payload = {}
        else:
            # or individual form fields:
            payload = request.form.to_dict()

        # Files
        excel_file = request.files.get('excel_file')   # <input name="sign" type="file" />
        dropbox_path = "/ID_card/file.txt"
        teachers_data = []


        # # Validate presence (customize as needed)
        if excel_file  :
            filename = secure_filename(excel_file.filename)
            temp_path = os.path.join('/tmp', filename)  # Use /tmp or another temp folder

            # Save file temporarily
            excel_file.save(temp_path)

            # Define Dropbox path (e.g., /uploads/filename.ext)
            dropbox_path = f"/ID_card/delete-{filename}"

            dbx = get_dropbox_client()
    
            # 2. Check if initialization was successful
            if dbx is None:
                print("Failed to initialize Dropbox client. Exiting.")
                return # Exit the script

            # 3. Attempt to upload the file
            # print(f"2. Attempting to upload '{LOCAL_UPLOAD_FILENAME}' to '{DROPBOX_FILE_PATH}'...")
            success = upload_file_dropbox(dbx, temp_path, dropbox_path)
    

            # Upload to Dropbox
            # success = upload_file_dropbox(temp_path, dropbox_path)

            start_row = int(payload.get("start_row_no",0))
            end_row = int(payload.get("end_row_no"))

            print(start_row,end_row)

            teachers_data = excel_to_dict(temp_path,start_row=start_row , end_row=end_row)
            teacher_phone_no = []
            deleted_teacher_count = 0

            for te in teachers_data :
                teacher_phone_no.append(int(te["phone"]))
                

            if success : 
                file_collection = get_collection('file')
                # print("after collection")
                result = file_collection.insert_one({ "type" : "teacher" ,"file_type" : "excel" , "operation" : "delete", "path" : dropbox_path , "timestamp" : datetime.now() })

                

                # Perform deletion
                teacher_collection = get_collection('teacher')
                result = teacher_collection.delete_many({ "phone": { "$in": teacher_phone_no } })
                deleted_teacher_count = result.deleted_count
                print(f"Deleted {result.deleted_count} documents.")


            os.remove(temp_path)

        
  
        # print(doc)
        return jsonify({
            "message": f"Drop {deleted_teacher_count} teachers successfully",

        }), 201

    except Exception as e:
        # log error in production
        return jsonify({"error": str(e)}), 500

