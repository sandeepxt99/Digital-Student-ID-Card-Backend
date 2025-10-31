from rembg import remove
from PIL import Image
import io

# 1. Define the input and output file paths
input_path = '../tmp/college sign.png'  # Make sure this file exists
output_path = '../tmp/college_sign.png'

# 2. Open the image file
try:
    with open(input_path, 'rb') as i:
        input_data = i.read()
except FileNotFoundError:
    print(f"Error: Input file '{input_path}' not found.")
    exit()

# 3. Process the image to remove the background
print("Removing background... This may take a moment.")
result_data = remove(input_data)
print("Background removal complete.")

# 4. Save the result to a new file
# Since the 'remove' function returns bytes, we use a bytes-based approach.
# If you want to use the PIL Image object directly:
image = Image.open(io.BytesIO(result_data))
image.save(output_path)

print(f"Result saved to {output_path}")