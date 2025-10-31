# from PIL import Image, ImageOps

# # Open your image
# img = Image.open("../tmp/college sign.png")

# # Invert colors
# inverted_img = ImageOps.invert(img.convert("RGB"))

# # Save the inverted image
# inverted_img.save("../tmp/sign_inverted.png")

# print("✅ Inverted image saved as sign_inverted.png")

from PIL import Image, ImageOps

# Open your image
img = Image.open("../tmp/sign_inverted.png").convert("RGBA")

# Convert image to grayscale (so you only have intensity)
gray = ImageOps.grayscale(img)

# Apply the new yellow color using the grayscale as a mask
# Yellow in RGB = (255, 255, 0)
yellow = Image.new("RGBA", img.size, (255, 255, 0, 255))
colored = Image.composite(yellow, img, gray)

# Save as PNG
colored.save("../tmp/sign_yellow.png", "PNG")

print("✅ Saved as sign_yellow.png")
