import qrcode
import os

# your website link
base_url = base_url = "http://10.101.101.153:8080/menu/"

# create qr folder automatically
os.makedirs("static/qrcodes", exist_ok=True)

# generate qr for tables 1 to 10
for table in range(1, 11):

    # url for each table
    url = f"{base_url}{table}"

    # create qr
    qr = qrcode.make(url)

    # save qr image
    qr.save(f"static/qrcodes/table_{table}.png")

print("QR Codes Generated Successfully")