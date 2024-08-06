import datetime
import cv2
from s3_file_manager import S3FileManager
import json
from pymongo_client import AtlasClient
from bson.objectid import ObjectId


config_list = json.load(open("data/config_list.json", "r"))
s3 = S3FileManager()

def get_home_page_introduction(course_id):
    if course_id not in config_list:
        return "Course not found"
    return config_list[course_id]["HOME_PAGE_INTRODUCTION"]


def get_module_video_link(course_id, module_num):
    if course_id not in config_list:
        return "Course not found"
    video_links = config_list[course_id]["VIDEOS_LINKS"]
    if module_num>=0 and module_num<len(video_links):
        return video_links[module_num]
    return "Module not found"


def get_module_slide(course_id, module_num):
    if course_id not in config_list:
        return "Course not found"
    slide_links = config_list[course_id]["SLIDES_LINKS"]
    if module_num>=0 and module_num<len(slide_links):
        content = s3.get_object(slide_links[module_num])
        return content
    return "Module not found"


def get_module_quiz(course_id, module_num):
    if course_id not in config_list:
        return "Course not found"
    quiz_links = config_list[course_id]["QUESTIONS_FILE"]
    content = s3.get_object(quiz_links[module_num])
    return content


def get_quiz_certificate(course_id, user_id):

    client = AtlasClient()
    # get user name from id
    user = client.find("users", {"_id": ObjectId(user_id)})

    if len(user)==0:
        return "User not found"
    user_name = user[0]["name"]
    certificate_image_path = config_list[course_id]["CERTIFICATE_PATH"]
    image = s3.get_object(certificate_image_path)

    certificate = cv2.imdecode(image, cv2.IMREAD_COLOR)
    font = cv2.FONT_HERSHEY_COMPLEX
    fontScale = 2
    original = cv2.putText(certificate, user_name, (
        50, 380), font, fontScale, (0, 0, 0), thickness=2)

    # add today's date
    original = cv2.putText(original, 
                           "Recorded on: " + datetime.datetime.now().strftime("%Y-%m-%d"), 
                           (850, 680), font, 0.7, (0, 0, 0), thickness=1)
    cv2.imwrite("Certificate.jpg", original)

