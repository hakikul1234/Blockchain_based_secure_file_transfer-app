from flask import Flask

UPLOAD_FOLDER = r"C:\Users\RAYEES\OneDrive\Desktop\Blockchain-based-Decentralized-File-Sharing-System-using-IPFS-master\Blockchain-based-Decentralized-File-Sharing-System-using-IPFS-master\main_server\Uploads"
DOWNLOAD_FOLDER = r"C:\Users\RAYEES\OneDrive\Desktop\Blockchain-based-Decentralized-File-Sharing-System-using-IPFS-master\Blockchain-based-Decentralized-File-Sharing-System-using-IPFS-master\main_server\Downloads"

app = Flask(__name__)
app.secret_key = "secret key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
app.config['BUFFER_SIZE'] = 64 * 1024
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['TWILIO_SID'] = "ACxxxxxxxxxxxxxxxxxx"
app.config['TWILIO_AUTH_TOKEN'] = "xxxxxxxxxxxxxxxxxxx"
app.config['TWILIO_PHONE'] = "+12567333160" 
