
from flask import Flask, json, jsonify, make_response, request, render_template
import requests, base64, sys
from io import BytesIO
from ftplib import FTP
import ftplib
import os
import io
import time
from configparser import ConfigParser

config = ConfigParser()
config.read('config.ini')

SITE_ID =  config['Site']['id']
print(SITE_ID)

web_server_api_endpoint = f"http://192.168.1.168:8080/sgems2/api/camera/sendDataPost"
res = requests.post(web_server_api_endpoint, data=SITE_ID)
cameras_list = res.json()['data']
print(type(cameras_list))