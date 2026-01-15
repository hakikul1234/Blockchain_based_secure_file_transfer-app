import os
import urllib.request
import requests  # <- new, replaces ipfsapi
from my_constants import app
import pyAesCrypt
from flask import Flask, flash, request, redirect, render_template, url_for, jsonify
from flask_socketio import SocketIO, send, emit
from werkzeug.utils import secure_filename
import socket
import pickle
from blockchain import Blockchain
import random
import time
from twilio.rest import Client


# -------------------- Setup --------------------
socketio = SocketIO(app)
blockchain = Blockchain()
otp_store = {}  
# format: { file_hash: (otp, expiry_time) }


IPFS_API = "http://127.0.0.1:5001/api/v0"  # local IPFS HTTP API

# -------------------- File Helpers --------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def append_file_extension(uploaded_file, file_path):
    file_extension = uploaded_file.filename.rsplit('.', 1)[1].lower()
    with open(file_path, 'a') as user_file:
        user_file.write('\n' + file_extension)

def decrypt_file(file_path, file_key):
    encrypted_file = file_path + ".aes"
    os.rename(file_path, encrypted_file)
    pyAesCrypt.decryptFile(encrypted_file, file_path,  file_key, app.config['BUFFER_SIZE'])

def encrypt_file(file_path, file_key):
    pyAesCrypt.encryptFile(file_path, file_path + ".aes",  file_key, app.config['BUFFER_SIZE'])

# -------------------- IPFS Functions --------------------
def hash_user_file(user_file, file_key):
    encrypt_file(user_file, file_key)
    encrypted_file_path = user_file + ".aes"

    # Upload to IPFS
    with open(encrypted_file_path, "rb") as f:
        files = {"file": f}
        response = requests.post(f"{IPFS_API}/add", files=files)
        response.raise_for_status()
        file_hash = response.json()["Hash"]

    # Pin the file so it stays in IPFS
    pin_response = requests.post(f"{IPFS_API}/pin/add", params={"arg": file_hash})
    pin_response.raise_for_status()
   

    return file_hash

def retrieve_from_hash(file_hash, file_key):
    file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], file_hash)
    os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

    response = requests.post(f"{IPFS_API}/cat", params={"arg": file_hash}, stream=True)

    if response.status_code != 200:
        raise Exception(f"IPFS could not find file {file_hash}: {response.text}")

    with open(file_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    decrypt_file(file_path, file_key)

    with open(file_path, 'rb') as f:
        lines = f.read().splitlines()
        last_line = lines[-1]
    file_extension = last_line.decode()
    saved_file = file_path + '.' + file_extension
    os.rename(file_path, saved_file)
    print(saved_file)

    return saved_file

def send_sms_otp(phone, otp):
    client = Client(
        app.config['TWILIO_SID'],
        app.config['TWILIO_AUTH_TOKEN']
    )

    client.messages.create(
        body=f"Your OTP for secure file download is: {otp}",
        from_=app.config['TWILIO_PHONE'],
        to=phone
    )


# -------------------- Flask Routes --------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/home')
def home():
    return render_template('index.html')

@app.route('/upload')
def upload():
    return render_template('upload.html', message="Welcome!")

@app.route('/download')
def download():
    return render_template('download.html', message="Welcome!")

@app.route('/connect_blockchain')
def connect_blockchain():
    is_chain_replaced = blockchain.replace_chain()
    return render_template('connect_blockchain.html', chain=blockchain.chain, nodes=len(blockchain.nodes))

@app.errorhandler(413)
def entity_too_large(e):
    return render_template('upload.html', message="Requested Entity Too Large!")

@app.route('/add_file', methods=['POST'])
def add_file():
    is_chain_replaced = blockchain.replace_chain()

    if is_chain_replaced:
        print('The nodes had different chains so the chain was replaced by the longest one.')
    else:
        print('All good. The chain is the largest one.')

    if request.method == 'POST':
        error_flag = True

        if 'file' not in request.files:
            message = 'No file part'
        else:
            user_file = request.files['file']

            if user_file.filename == '':
                message = 'No file selected for uploading'

            if user_file and allowed_file(user_file.filename):
                error_flag = False

                filename = secure_filename(user_file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                user_file.save(file_path)

                append_file_extension(user_file, file_path)

                sender = request.form['sender_name']
                receiver = request.form['receiver_name']
                file_key = request.form['file_key']

                # 🔐 NEW: Receiver phone number
                receiver_phone = request.form['receiver_phone']

                try:
                    # Upload to IPFS
                    hashed_output1 = hash_user_file(file_path, file_key)

                    # Add to blockchain
                    index = blockchain.add_file(sender, receiver, hashed_output1)

                    # ======================
                    # 🔐 OTP GENERATION
                    # ======================
                    otp = random.randint(100000, 999999)
                    expiry = time.time() + 300  # 5 minutes

                    otp_store[hashed_output1] = (str(otp), expiry)

                    # Send OTP via SMS
                    send_sms_otp(receiver_phone, otp)

                    print("OTP sent:", otp)  # for testing only

                except Exception as err:
                    message = str(err)
                    error_flag = True
                    if "ConnectionError:" in message:
                        message = "Gateway down or bad Internet!"

            else:
                error_flag = True
                message = 'Allowed file types are txt, pdf, png, jpg, jpeg, gif'

        if error_flag:
            return render_template('upload.html', message=message)
        else:
            return render_template(
                'upload.html',
                message="File uploaded successfully. OTP sent to receiver mobile.")

@app.route('/retrieve_file', methods=['POST'])
def retrieve_file():
    is_chain_replaced = blockchain.replace_chain()

    if is_chain_replaced:
        print('The nodes had different chains so the chain was replaced by the longest one.')
    else:
        print('All good. The chain is the largest one.')

    if request.method == 'POST':
        error_flag = True

        # 🔐 Get form values
        file_hash = request.form.get('file_hash')
        file_key = request.form.get('file_key')
        entered_otp = request.form.get('otp')

        if file_hash == '':
            message = 'No file hash entered.'
        elif file_key == '':
            message = 'No file key entered.'
        elif entered_otp == '':
            message = 'OTP is required.'
        else:
            # ======================
            # 🔐 OTP VERIFICATION
            # ======================
            if file_hash not in otp_store:
                message = 'OTP not found or already used.'
                error_flag = True
            else:
                saved_otp, expiry = otp_store[file_hash]

                if time.time() > expiry:
                    del otp_store[file_hash]
                    message = 'OTP expired. Please request again.'
                    error_flag = True
                elif entered_otp != saved_otp:
                    message = 'Invalid OTP.'
                    error_flag = True
                else:
                    # OTP valid → remove OTP
                    del otp_store[file_hash]

                    error_flag = False
                    try:
                        retrieve_from_hash(file_hash, file_key)
                    except Exception as err:
                        message = str(err)
                        error_flag = True
                        if "ConnectionError:" in message:
                            message = "Gateway down or bad Internet!"

        if error_flag:
            return render_template('download.html', message=message)
        else:
            return render_template(
                'download.html',
                message="File successfully downloaded after OTP verification"
            )

@app.route('/get_chain', methods=['GET'])
def get_chain():
    response = {'chain': blockchain.chain,
                'length': len(blockchain.chain)}
    return jsonify(response), 200

# -------------------- SocketIO --------------------
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    print(request)

@socketio.on('add_client_node')
def handle_node(client_node):
    print(client_node)
    blockchain.nodes.add(client_node['node_address'])
    emit('my_response', {'data': pickle.dumps(blockchain.nodes)}, broadcast=True)

@socketio.on('remove_client_node')
def handle_node(client_node):
    print(client_node)
    blockchain.nodes.remove(client_node['node_address'])
    emit('my_response', {'data': pickle.dumps(blockchain.nodes)}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')
    print(request)

# -------------------- Main --------------------
if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=5111)
