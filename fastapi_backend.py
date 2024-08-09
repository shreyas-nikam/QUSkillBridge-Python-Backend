from fastapi import FastAPI, Response
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from utils import update_profile, get_course_outline, generate_cover_letter, get_skill_match_score
from course_utils import get_course_modules_list, get_home_page_introduction, get_module_video_link, get_module_slide, get_module_quiz, get_quiz_certificate, get_chat_response           

app = FastAPI()


# Allow CORS for the frontend
origins = [
    "http://localhost:3000",  # React frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# test connection
@app.get("/")
def read_root():
    return {"Hello": "World"}

# get profile suggestions
@app.post("/get_profile_suggestions")
def get_profile_suggestions(data: dict):
    """
    Get the profile suggestions for a given profile
    
    Args:
    data: dict - dictionary containing the linkedin_profile_id
    """
    profile_id = data.get("linkedin_profile_id")
    return update_profile(profile_id)

# get course outline
@app.post("/generate_course_outline")
def get_course_outline_api(data: dict):
    """
    Get the course outline for a given profile and job

    Args:
    data: dict - dictionary containing the profile_id and job_id
    """
    profile_id, job_id, feedback = data.get("profile_id"), data.get("job_id"), data.get("feedback")
    return get_course_outline(profile_id, job_id, feedback)

# generate cover letter
@app.post("/generate_cover_letter")
def generate_cover_letter_api(data: dict):
    """
    Generate a cover letter for a given profile and job

    Args:
    data: dict - dictionary containing the profile_id and job
    """
    profile_id, job_id = data.get("profile_id"), data.get("job_id")
    return generate_cover_letter(profile_id=profile_id, job_id=job_id)

# get skill match score
@app.post("/generate_skill_match_score")
def get_skill_match_score_api(data: dict):
    """
    Get the skill match score between a profile and a job
    
    Args:
    data: dict - dictionary containing the profile_id and job_id
    """
    profile_id, job_id = data.get("profile_id"), data.get("job_id")
    return get_skill_match_score(profile_id, job_id)


# course related routes

# get course modules
@app.get("/courses/{course_id}/modules")
def get_course_modules_api(course_id: str):
    return get_course_modules_list(course_id)

# get home page
@app.get("/courses/{course_id}/home_page_introduction")
def get_home_page_introduction_api(course_id: str):
    return get_home_page_introduction(course_id)

# get video link for a module in a course
@app.get("/courses/{course_id}/module/{module_num}/video_link")
def get_module_video_link_api(course_id: str, module_num: int):
    return get_module_video_link(course_id, module_num)

# get slide link for a module in a course
@app.get("/courses/{course_id}/module/{module_num}/slides")
def get_module_slide_link_api(course_id: str, module_num: int):
    content = get_module_slide(course_id, module_num)
    return Response(content, media_type="application/pdf")

# get quiz questions for a module in a course
@app.get("/courses/{course_id}/quiz")
def get_module_quiz_api(course_id: str):
    content = get_module_quiz(course_id)
    return Response(content, media_type="application/json")

# get quiz certificate on completion for a user
@app.get("/courses/{course_id}/quiz_certificate/{user_id}")
def get_quiz_certificate_api(course_id: str, user_id: str):
    return  get_quiz_certificate(course_id, user_id)

# get chat response
@app.post("/chat")
def get_chat_response_api(data: dict):
    """
    Get the chat response for a given message
    
    Args:
    data: dict - dictionary containing the message
    """
    course_id, history, query = data.get("course_id"), data.get("history"), data.get("query")
    return get_chat_response(course_id, history, query)