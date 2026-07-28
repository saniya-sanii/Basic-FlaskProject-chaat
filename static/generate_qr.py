import qrcode
import os

# Base URL pointing to local server menu route
base_url = "http://localhost:8080/menu/"

# Ensure the static/qrcodes/ folder exists
os.makedirs("static/qrcodes", exist_ok=True)

print("Starting QR Code Generation for tables...")

# Generate QR codes for tables 1 to 8
for table in range(1, 9):
    url = f"{base_url}{table}"
    
    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save the QR code image
    img_path = f"static/qrcodes/table_{table}.png"
    img.save(img_path)
    print(f"Generated QR Code for Table {table} -> {url} [Saved: {img_path}]")

print("All QR Codes Generated Successfully!")