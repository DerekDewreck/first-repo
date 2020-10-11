from flask import Flask, json, jsonify, make_response, request, render_template
import requests, base64, sys
from io import BytesIO
from ftplib import FTP
import ftplib
import os
import io
import time
from configparser import ConfigParser
app = Flask(__name__)

# USER_NAME = 'admin'
# PASSWORD = 'pg96kcjc'
# CAMERA_IP = '192.168.1.190'
config = ConfigParser()
config.read('config.ini')
WEB_IP_ADDRESS = config['Web-Server-SGEMS2']['ip-address']
WEB_PORT = config['Web-Server-SGEMS2']['port']
WEB_SERVER = f"{WEB_IP_ADDRESS}:{WEB_PORT}"
# WEB_SERVER= "192.168.1.168:8080"
# BASE_URL = f"http://{USER_NAME}:{PASSWORD}@"
cameras_list =[]
LPR_TYPE = config['LPR']['type']

@app.route("/", methods=["GET"])
def home():
    return f"{request.environ['REMOTE_ADDR']}:{request.environ['REMOTE_PORT']}"

# The camera will send a get request to the '/detected' route when there is a detection of license plate 
@app.route("/detected", methods=["GET"] )
def detected():
    print("--------------------Camera detected a license plate--------------------")
    # incoming_cam_ip_addr = request.remote_addr
    incoming_cam_ip_addr = request.environ['REMOTE_ADDR']
    incoming_cam_port = request.environ['REMOTE_PORT']
    print(f"Camera ip address: {incoming_cam_ip_addr}")
    print(f"Cam port:{incoming_cam_port}")
    print (request)
    incoming_camera = get_incoming_camera_details(incoming_cam_ip_addr, incoming_cam_port)
    if incoming_camera:
        print("INCOMING CAMERA")
        print(f"USERNAME: {incoming_camera['username']}")
        print(f"PASSWORD: {incoming_camera['password']}")
        print(f"IP ADDR: {incoming_camera['ip_address']}")

        data_dict = api_get_data(incoming_cam_ip_addr,incoming_cam_port,incoming_camera)
        send_data_to_webserver(data_dict)
        ftp_data = get_data_from_ftp_server(data_dict)
        send_data_to_webserver(ftp_data, is_ftp=True)
    else:
        print("No Matching CAMERA found in the database")
    print("--------------------License plate detection processing finished --------------------")
    return "Detected"


def get_incoming_camera_details(incoming_cam_ip_addr, incoming_cam_port):
    print("called get_incoming_camera_details(incoming_cam_ip_addr)")
    web_server_api_endpoint = f"http://{WEB_SERVER}/sgems2/api/camera/sendData"
    res = requests.get(web_server_api_endpoint)
    cameras_list = res.json()['data']
    incoming_camera = {}
    if cameras_list:
        for camera in cameras_list:
            if LPR_TYPE == "lpr":    
                # The port number is only checked if the LPR modules is being used across different networks (NAT)
                if camera['public_ip'] == incoming_cam_ip_addr:
                    incoming_camera = camera 
            else: 
                # For LPR Lite, there is no need to check for the port number as the cameras and the servers are in the same network
                if camera['ip_address'] == incoming_cam_ip_addr:
                    incoming_camera = camera 

    return incoming_camera

def send_data_to_webserver(data_dict, is_ftp=False):
    print("called send_data_to_webserver(data_dict)")
    if is_ftp:
        web_server_api_endpoint = f"http://{WEB_SERVER}/sgems2/api/camera/receiveBinaryData"
    else:
        web_server_api_endpoint = f"http://{WEB_SERVER}/sgems2/api/camera/receiveData"
    header = {"content-type": "application/json"}
    res = requests.post(
        web_server_api_endpoint,
        data=json.dumps(data_dict),
        headers=header
    )


# api_get_data will send a get request to the camera api to retrieve the latest license plate to be detected 
def api_get_data(incoming_cam_ip_addr,incoming_cam_port, incoming_camera):
    print("called api_get_data(incoming_cam_ip_addr, incoming_camera)")
    if LPR_TYPE == "lpr":     
        BASE_URL = f"http://{incoming_camera['username']}:{incoming_camera['password']}@{incoming_cam_ip_addr}:{incoming_camera['port']}"
    else:
        BASE_URL = f"http://{incoming_camera['username']}:{incoming_camera['password']}@{incoming_cam_ip_addr}"
    # print(f"BASE_URL -- {BASE_URL}")
    data_dict = {}

    # Calls the camera api to get the time, plate number and plate image path (stored on camera)
    api_end_point = f"{BASE_URL}/cgi-bin/operator/operator.cgi?action=get.lpr.lastdata&type=1"
    res = requests.get(api_end_point)
    res_data = res.content.decode('utf-8')
    res_data = res_data.split(";")
    data_dict["time"] = res_data[0].split("=")[1].strip().replace("\'","")
    data_dict["plate_num"] = res_data[1].split("=")[1].strip().replace("\'","")
    data_dict["plate_img_path"] = res_data[2].split("=")[1].strip().replace("\'","")


    # Call the camera api to get system information, hardware address, camera name
    api_end_point = f"{BASE_URL}/cgi-bin/admin/admin.cgi?action=get.system.information"
    res = requests.get(api_end_point)
    res_data = res.content.decode('utf-8')
    res_data = res_data.split(";")
    data_dict["hwaddress"] = res_data[4].split("=")[1].strip().replace("\'","")
    data_dict["cam_name"] = res_data[16].split("=")[1].strip().replace("\'","")


    # Call the camera api to get information about the ftp server the camera is sending data to
    api_end_point = f"{BASE_URL}/cgi-bin/operator/operator.cgi?action=get.event.server"
    res = requests.get(api_end_point)
    res_data = res.content.decode('utf-8')
    res_data = res_data.split(";")
    data_dict["ftp_server"] = res_data[2].split("=")[1].strip().replace("\'","")
    data_dict["ftp_port"] = incoming_camera['ftp_port']
    data_dict["ftp_username"] = res_data[4].split("=")[1].strip().replace("\'","")
    data_dict["ftp_password"] = res_data[5].split("=")[1].strip().replace("\'","")
    data_dict["ftp_file_path"] = incoming_camera['ftp_file_path']

    # Call the camera api to get the license plate image (small image) from the license plate image path
    api_end_point = f"{BASE_URL}/{data_dict['plate_img_path']}"
    res = requests.get(api_end_point)
    data_dict["lp_img_base64"] = ("data:" + 
         res.headers['Content-Type'] + ";" +
        "base64," + base64.b64encode(res.content).decode("utf-8"))

    data_dict["camera_ip_address"] = incoming_cam_ip_addr
    return data_dict

# get_data_from_ftp_serve(data_dict) is called to get data stored in the ftp server (sent by the camera when there is a detection)
def get_data_from_ftp_server(data_dict):
    print("called get_data_from_ftp_server(data_dict)")
    time.sleep(2)
    small_img_dict = {}
    big_img_dict = {}
    avi_list= []
    r = io.BytesIO()
    file_mapper = {}
    file_mapper["hwaddress"] = data_dict["hwaddress"]
    file_mapper["time"] = data_dict["time"]
    file_mapper["plate_num"] = data_dict["plate_num"]
    file_mapper["big_ftp_img_file"] = ""
    file_mapper["small_ftp_img_file"] = ""
    file_mapper["avi_vid_file"] = ""

    try:
        with FTP() as ftp:
            print(f"ftp server: {data_dict['ftp_server'].strip()}\nusername: { data_dict['ftp_username']}\npassword: {data_dict['ftp_password']}")
            ftp.connect(host=data_dict["ftp_server"], port=int(data_dict["ftp_port"]))
            ftp.login(user=data_dict["ftp_username"],passwd= data_dict["ftp_password"])
            ftp.set_pasv(True)
            ftp.cwd(data_dict["ftp_file_path"] )
            
            for file in ftp.nlst():
                file_type = file[-3:]
                if data_dict["plate_num"] in file:
                        if file_type == "jpeg" or file_type == "jpg" or file_type == "png":
                            print(f"\nDownloading {file}")
                            ftp.retrbinary(f"RETR {file}", r.write)
                            # r_base64= f"data:image/{file_type};base64,{base64.b64encode(r.getvalue()).decode('utf-8')}"
                            r_base64= f"{base64.b64encode(r.getvalue()).decode('utf-8')}"
                            if "LPR-Visitor-Network Camera" in file:
                                file_mapper["big_ftp_img_file"] = r_base64
                            else:
                                file_mapper["small_ftp_img_file"] = r_base64
                elif file_type == "avi":
                    print(f"\nDownloading {file}")
                    ftp.retrbinary(f"RETR {file}", r.write)
                    r_base64= f"data:video/{file_type};base64,{base64.b64encode(r.getvalue()).decode('utf-8')}"
                    avi_list.append(r_base64)
                print(f"\nDeleting {file}")
                ftp.delete(file)
            # r.close()
            ftp.quit()
    except ftplib.all_errors as e:
        print(e)
    finally:
        r.close()     

    if len(avi_list) > 0:
        print("------------ avi files ---------------")
        print(f"AVI list len --> {len(avi_list)}")
        file_mapper["avi_vid_file"] = avi_list[len(avi_list)-1]

    return file_mapper

def main():
    print("flask server started")
    print(WEB_SERVER)
    app.run(host="0.0.0.0", port = "6000",debug=True, use_reloader=False)
    
if __name__ == "__main__":
    main()