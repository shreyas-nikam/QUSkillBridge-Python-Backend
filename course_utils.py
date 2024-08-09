import io
import datetime
import cv2
from s3_file_manager import S3FileManager
import json
from pymongo_client import AtlasClient
from bson.objectid import ObjectId
import base64
from chatbot import ChatBot
import numpy as np


config_list = json.load(open("data/config_list.json", "r"))
s3 = S3FileManager()
atlas_client = AtlasClient()

def get_course_modules_list(course_id):
    # get course name from id
    course = atlas_client.find("courses", {"_id": ObjectId(course_id)})
    if len(course)==0:
        return "Course not found"
    course_id = course[0]["app_code"]

    if course_id not in config_list:
        return "Course not found"
    return config_list[course_id]["COURSE_NAMES_VIDEOS"]

def get_home_page_introduction(course_id):
    # get course name from id
    course = atlas_client.find("courses", {"_id": ObjectId(course_id)})
    if len(course)==0:
        return "Course not found"
    course_id = course[0]["app_code"]

    if course_id not in config_list:
        return "Course not found"
    return config_list[course_id]["HOME_PAGE_INTRODUCTION"]


def get_module_video_link(course_id, module_num):
    # get course name from id
    course = atlas_client.find("courses", {"_id": ObjectId(course_id)})
    if len(course)==0:
        return "Course not found"
    course_id = course[0]["app_code"]

    if course_id not in config_list:
        return "Course not found"
    video_links = config_list[course_id]["VIDEOS_LINKS"]
    if module_num>=0 and module_num<len(video_links):
        return video_links[module_num]
    return "Module not found"


def get_module_slide(course_id, module_num):
    # get course name from id
    course = atlas_client.find("courses", {"_id": ObjectId(course_id)})
    if len(course)==0:
        return "Course not found"
    course_id = course[0]["app_code"]

    if course_id not in config_list:
        return "Course not found"
    slide_links = config_list[course_id]["SLIDES_LINKS"]
    if module_num>=0 and module_num<len(slide_links):
        response = s3.get_object(slide_links[module_num])
        pdf_content = response
        pdf_base_64 = base64.b64encode(pdf_content).decode('utf-8')
        return pdf_base_64
    return "Module not found"


def get_module_quiz(course_id):
    # get course name from id
    course = atlas_client.find("courses", {"_id": ObjectId(course_id)})
    if len(course)==0:
        return "Course not found"
    course_id = course[0]["app_code"]

    if course_id not in config_list:
        return "Course not found"
    quiz_links = config_list[course_id]["QUESTIONS_FILE"]
    content = s3.get_object(quiz_links)
    return content


def get_quiz_certificate(course_id, user_id):
    # get user name from id
    user = atlas_client.find("users", {"_id": ObjectId(user_id)})

    course=atlas_client.find("courses", {"_id": ObjectId(course_id)})
    if len(course)==0:
        return "Course not found"
    course_id = course[0]["app_code"]

    if len(user)==0:
        return "User not found"
    user_name = user[0]["name"]
    certificate_image_path = config_list[course_id]["CERTIFICATE_PATH"]
    image_content = s3.get_object(certificate_image_path)

    image_np = np.frombuffer(image_content, dtype=np.uint8)
    certificate = cv2.imdecode(image_np, cv2.IMREAD_COLOR)

    # add user name to certificate
    font = cv2.FONT_HERSHEY_COMPLEX
    fontScale = 3
    cv2.putText(certificate, user_name, (
        145, 800), font, fontScale, (0, 0, 0), thickness=3)

    # add today's date
    cv2.putText(certificate, 
                           "Recorded on: " + datetime.datetime.now().strftime("%Y-%m-%d"), 
                           (1630, 1095), font, 0.7, (0, 0, 0), thickness=1)
                           
    
    # Encode the modified image to send back to client
    _, buffer = cv2.imencode('.jpg', certificate)
    io_buf = io.BytesIO(buffer)

    # Encode image as base64 to embed in JSON
    io_buf.seek(0)
    base64_data = base64.b64encode(io_buf.read()).decode('utf-8')

    return base64_data



def get_chat_response(course_id, history, query):
    course = atlas_client.find("courses", {"_id": ObjectId(course_id)})
    if len(course)==0:
        return "Course not found"
    course_id = course[0]["app_code"]

    chatbot_locations = {
        "NIST":"chatbot/qu-nist/test/retriever",
        "AIRMF":"chatbot/qu-airmf/test/retriever",
        "AIBDI":"chatbot/qu-aibdi/test/retriever",
        "AEDT":"chatbot/qu-aedt/test/retriever",
        "CONSU":"chatbot/qu-consu/test/retriever",
        "AGIRM":"chatbot/qu-agirm/test/retriever",
        "SCFACO":"chatbot/qu-scfaco/test/retriever",
        "SGMRM":"chatbot/qu-sgmrm/test/retriever",
        "GENPRO":"chatbot/qu-genpro/test/retriever",
        "SCFACONLP":"chatbot/qu-scfaconlp/test/retriever",
        "PRMST":"chatbot/qu-prmst/test/retriever",
        "GSCRRMF":"chatbot/qu-gscrrmf/test/retriever",
        "SROBOM":"chatbot/qu-srobom/test/retriever",
    }

    if course_id not in chatbot_locations:
        return "This course does not support a chatbot yet"
    
    chatbot_location = chatbot_locations[course_id]
    print(chatbot_location)
    chatbot = ChatBot(chatbot_location)
    response = chatbot.get_response(history, query)
    return response



    