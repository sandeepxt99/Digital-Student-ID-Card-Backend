import qrcode

# Create QR code instance

def make_qr_code(data,output_path="../tmp/qrcode.png"):
    qr = qrcode.QRCode(
    version=1,  # Controls the size of the QR Code (1–40)
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,  # Size of each box in pixels
    border=4,  # Border thickness
    )

    # Add data
    qr.add_data(data)
    qr.make(fit=True)

    # Create an image from the QR Code instance
    img = qr.make_image(fill_color="black", back_color="transparent").convert("RGBA")

    # Save the image
    img.save(output_path)

    print("✅ QR code generated and saved as 'qrcode.png'")
