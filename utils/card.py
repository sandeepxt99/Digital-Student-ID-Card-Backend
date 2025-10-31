import base64
from lxml import etree
import requests
import os

# --- 1. CONFIGURATION ---

# Paths for the SVG template and the final output
# FIX 1: Corrected the path to match the template file name 'id_card_template.svg'
# Updated path as requested by the user:
SVG_TEMPLATE_PATH = "id_card_front_template.svg" 
# Updated path as requested by the user:
OUTPUT_PATH = "../tmp/student_id_card_merged.svg"

# XML Namespace definitions for SVG parsing
SVG_NS = 'http://www.w3.org/2000/svg'
XLINK_NS = 'http://www.w3.org/1999/xlink'
ns = {'svg': SVG_NS, 'xlink': XLINK_NS}

# # --- 2. STUDENT DATA (Dynamic Input) ---
# student_data = {
#     "college_name": "Indian Engineering Colleges", 
#     "name": "ISABELLA WONG",
#     "roll_no": "2024-ME-901",
#     "dob": "11/05/2001",
#     "class": "Ph.D. Robotics",
#     "father_name": "DAVID WONG",
#     "valid_session": "2024-2027",
    
#     # Address is split into lines that visually fit the 200px photo width
#     "address": "Research Avenue, Suite 400 Panchkula Haryana(134101)",
    
#     # Real, working, public image URLs for better visual appeal
#     "profile_url": "https://res.cloudinary.com/dr9w7oyqe/image/upload/v1760940404/student/ex32shyilciahvdrcyd7.png", # Sample Portrait (Unsplash)
#     "college_logo_url": "https://res.cloudinary.com/dr9w7oyqe/image/upload/v1761218446/local_uploads/my_disk_file.jpg", # Wikimedia Placeholder Logo
#     "college_sign_url": "https://res.cloudinary.com/dr9w7oyqe/image/upload/v1761220064/local_uploads/kmkyjzyfb3bla7lkoiqr.png", # Sample Signature 1 (Imgur)
#     "student_sign_url": "https://res.cloudinary.com/dr9w7oyqe/image/upload/v1761220064/local_uploads/kmkyjzyfb3bla7lkoiqr.png", # Sample Signature 2 (Imgur)
# }

# --- 3. HELPER FUNCTIONS ---

def get_image_base64(image_path_or_url, placeholder_text="IMAGE", is_logo=False):
    """Fetches image data from a URL or local file and returns its Base64 encoding."""
    
    try:
        # 1. Fetch image content
        # Use a user-agent to avoid being blocked by some sites
        headers = {'User-Agent': 'Mozilla/5.0'} 
        if image_path_or_url.startswith('http'):
            response = requests.get(image_path_or_url, headers=headers, timeout=10)
            response.raise_for_status() 
            image_bytes = response.content
            mime_type = response.headers.get('Content-Type', 'image/png').split(';')[0]
        else:
            with open(image_path_or_url, "rb") as f:
                image_bytes = f.read()
            mime_type = "image/png"
            
    except Exception as e:
        print(f"Warning: Could not fetch image for {image_path_or_url}. Using SVG placeholder. Error: {e}")
        # 2. Fallback to a solid color SVG placeholder if fetch fails
        if placeholder_text == "Profile": w, h, color = 200, 240, "#D4D4D4"
        elif placeholder_text == "Logo": w, h, color = 70, 70, "#FFC72C"
        else: w, h, color = 180, 50, "#E0E0E0" # Signatures
            
        svg_placeholder = f"""
        <svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">
            <rect width="100%" height="100%" fill="{color}"/>
            <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-size="20" fill="#333333">{placeholder_text}</text>
        </svg>
        """
        encoded_svg = base64.b64encode(svg_placeholder.encode('utf-8')).decode('utf-8')
        return f"data:image/svg+xml;base64,{encoded_svg}"

    # 3. Encode the image bytes to Base64 and create data URI
    encoded_image = base64.b64encode(image_bytes).decode('utf-8')
    return f"data:{mime_type};base64,{encoded_image}"

def replace_text_by_id(root, element_id, new_text):
    """Finds an element by its ID and replaces the content of its immediate tspan or text node."""
    element = root.xpath(f"//*[@id='{element_id}']", namespaces=ns)
    if element:
        element[0].text = new_text
        # print(f"Text ID '{element_id}' replaced.")
    else:
        print(f"Error: Text ID '{element_id}' not found.")

def replace_image_by_id(root, placeholder_id, image_data_uri):
    """Replaces a rectangular placeholder with an SVG <image> tag containing Base64 data."""
    placeholder = root.xpath(f"//*[@id='{placeholder_id}']", namespaces=ns)
    
    if placeholder:
        placeholder_element = placeholder[0]
        
        # 1. Get position and size attributes from the placeholder <rect>
        x = placeholder_element.get('x')
        y = placeholder_element.get('y')
        width = placeholder_element.get('width')
        height = placeholder_element.get('height')
        
        # 2. Create the new <image> element
        image_tag = etree.Element(etree.QName(SVG_NS, 'image'), nsmap=root.nsmap)
        image_tag.set('x', x)
        image_tag.set('y', y)
        image_tag.set('width', width)
        image_tag.set('height', height)
        # Use the correct xlink:href attribute for the data URI
        image_tag.set(etree.QName(XLINK_NS, 'href'), image_data_uri)
        
        # 3. Insert the new image and remove the old placeholder rectangle
        parent = placeholder_element.getparent()
        parent.insert(parent.index(placeholder_element), image_tag)
        parent.remove(placeholder_element)
        # print(f"Image placeholder '{placeholder_id}' replaced.")
    else:
        print(f"Error: Image placeholder '{placeholder_id}' not found.")


# --- 4. MAIN MERGING LOGIC ---

def merge_svg_template_front(data,SVG_TEMPLATE_PATH="other/id_card_front_template.svg",OUTPUT_PATH="../tmp/student_id_card_front.svg" ):
    """Main function to perform data merging into the SVG template."""
    
    # 1. Load the template SVG
    try:
        # FIX 2: Using etree.parse(file_path) is safer and handles XML structure better than 
        # reading to string and then calling etree.fromstring()
        tree = etree.parse(SVG_TEMPLATE_PATH)
        root = tree.getroot()
    except FileNotFoundError:
        print(f"FATAL ERROR: Could not find SVG template file. Path checked: '{SVG_TEMPLATE_PATH}'.")
        print("Please ensure you have saved the 'ID Card SVG Template' file.")
        return
    except Exception as e:
        print(f"FATAL ERROR: Failed to parse SVG template file. Error details: {e}")
        return

    # 2. Replace Text Fields
    text_map = {
        "text-college-name": data["college_name"],
        "text-student-name": data["name"],
        "text-roll-no": data["roll_no"],
        "text-dob": data["dob"],
        "text-class": data["class"],
        "text-father-name": data["father_name"],
        "text-valid-session": data["valid_session"],
        "text-address": data["address"],
    }
    
    for element_id, new_text in text_map.items():
        replace_text_by_id(root, element_id, new_text)

    # 3. Embed Images (fetch data and replace placeholders)
    
    profile_uri = get_image_base64(data["profile_url"], placeholder_text="Profile")
    replace_image_by_id(root, "placeholder-profile-photo", profile_uri)
    
    logo_uri = get_image_base64(data["college_logo_url"], placeholder_text="Logo", is_logo=True)
    replace_image_by_id(root, "placeholder-college-logo", logo_uri)
    
    college_sign_uri = get_image_base64(data["college_sign_url"], placeholder_text="C. Sign")
    replace_image_by_id(root, "placeholder-college-sign", college_sign_uri)
    
    student_sign_uri = get_image_base64(data["student_sign_url"], placeholder_text="S. Sign")
    replace_image_by_id(root, "placeholder-student-sign", student_sign_uri)

    # 4. Save the final merged SVG
    try:
        # Ensure the directory exists before writing
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        et = etree.ElementTree(root)
        et.write(OUTPUT_PATH, pretty_print=True, xml_declaration=True, encoding="utf-8")
        print(f"\nSUCCESS: Final ID card SVG saved to: {OUTPUT_PATH}")
    except Exception as e:
        print(f"Error saving file: {e}")


def merge_svg_template_back(data,SVG_TEMPLATE_PATH="other/id_card_back_template.svg",OUTPUT_PATH="../tmp/student_id_card_back.svg" ):
    """Main function to perform data merging into the SVG template."""
    
    # 1. Load the template SVG
    try:
        # FIX 2: Using etree.parse(file_path) is safer and handles XML structure better than 
        # reading to string and then calling etree.fromstring()
        tree = etree.parse(SVG_TEMPLATE_PATH)
        root = tree.getroot()
    except FileNotFoundError:
        print(f"FATAL ERROR: Could not find SVG template file. Path checked: '{SVG_TEMPLATE_PATH}'.")
        print("Please ensure you have saved the 'ID Card SVG Template' file.")
        return
    except Exception as e:
        print(f"FATAL ERROR: Failed to parse SVG template file. Error details: {e}")
        return

    # 2. Replace Text Fields
    text_map = {
        "college-name": data.get("college_name", ""),
        "student-contact": data.get("student_contact", ""),
        "college-line1": data.get("college_line1", ""),
        "college-line2": data.get("college_line2", ""),
        "college-contact": data.get("college_contact", ""),
        "date-issued": data.get("date_issued", ""),
        "footer-info": data.get("footer-info", ""),
    }
    
    for element_id, new_text in text_map.items():
        replace_text_by_id(root, element_id, new_text)

    # 3. Embed Images (fetch data and replace placeholders)
    
    qrcode_uri = get_image_base64(data.get("qr_code_url"), placeholder_text="QRcode")
    replace_image_by_id(root, "qr-placeholder", qrcode_uri)
    
    # 4. Save the final merged SVG
    try:
        # Ensure the directory exists before writing
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        et = etree.ElementTree(root)
        et.write(OUTPUT_PATH, pretty_print=True, xml_declaration=True, encoding="utf-8")
        print(f"\nSUCCESS: Final ID card SVG saved to: {OUTPUT_PATH}")
    except Exception as e:
        print(f"Error saving file: {e}")


# for teacher only


def merge_svg_template_front_teacher(data,SVG_TEMPLATE_PATH="other/teacher_id_card_front_template.svg",OUTPUT_PATH="../tmp/teacher_id_card_front.svg" ):
    """Main function to perform data merging into the SVG template."""
    
    # 1. Load the template SVG
    try:
        # FIX 2: Using etree.parse(file_path) is safer and handles XML structure better than 
        # reading to string and then calling etree.fromstring()
        tree = etree.parse(SVG_TEMPLATE_PATH)
        root = tree.getroot()
    except FileNotFoundError:
        print(f"FATAL ERROR: Could not find SVG template file. Path checked: '{SVG_TEMPLATE_PATH}'.")
        print("Please ensure you have saved the 'ID Card SVG Template' file.")
        return
    except Exception as e:
        print(f"FATAL ERROR: Failed to parse SVG template file. Error details: {e}")
        return

    # 2. Replace Text Fields
    text_map = {
        "text-college-name": data["college_name"],
        "text-teacher-name": data["name"],
        "text-qualification": data["qualification"],
        "text-dob": data["dob"],
        "text-designation": data["designation"],
        "text-phone": data["phone"],
        "text-address": data["address"],
    }
    
    for element_id, new_text in text_map.items():
        replace_text_by_id(root, element_id, new_text)

    # 3. Embed Images (fetch data and replace placeholders)
    
    profile_uri = get_image_base64(data["profile_url"], placeholder_text="Profile")
    replace_image_by_id(root, "placeholder-profile-photo", profile_uri)
    
    logo_uri = get_image_base64(data["college_logo_url"], placeholder_text="Logo", is_logo=True)
    replace_image_by_id(root, "placeholder-college-logo", logo_uri)
    
    college_sign_uri = get_image_base64(data["college_sign_url"], placeholder_text="C. Sign")
    replace_image_by_id(root, "placeholder-college-sign", college_sign_uri)
    
    teacher_sign_uri = get_image_base64(data["teacher_sign_url"], placeholder_text="S. Sign")
    replace_image_by_id(root, "placeholder-teacher-sign", teacher_sign_uri)

    # 4. Save the final merged SVG
    try:
        # Ensure the directory exists before writing
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        et = etree.ElementTree(root)
        et.write(OUTPUT_PATH, pretty_print=True, xml_declaration=True, encoding="utf-8")
        print(f"\nSUCCESS: Final ID card SVG saved to: {OUTPUT_PATH}")
    except Exception as e:
        print(f"Error saving file: {e}")



# if __name__ == "__main__":
#     print("Starting SVG merging process with updated centering and alignment...")
#     # NOTE: Ensure the 'ID Card SVG Template' file is saved as 'id_card_template.svg' 
#     # in the same directory where this script is executed.
#     student_data = {
#     "college_name": "Greenwood University",
#     "student_contact": "student@example.com",
#     "college_line1": "123 College St.",
#     "college_line2" : "Panchkula",
#     "college_contact": "info@greenwood.edu",
#     "date_issued": "2025-10-24",
#     "footer-info" : "Powered by ID Card Generator",
#     }
#     merge_svg_template_back(student_data)

