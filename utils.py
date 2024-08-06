from bson.objectid import ObjectId
import time
import json
from langchain_core.prompts import PromptTemplate

from llm import LLM
import random

from urllib.parse import urlencode
from jobspy import scrape_jobs
import ast
import logging

from pymongo_client import AtlasClient



def get_response_from_llm(llm, prompt, inputs, output_type="json"):
    trials = 5
    for _ in range(trials):
        try:
            time.sleep(random.randint(1, 3))
            response = llm.get_response(prompt, inputs=inputs)
            if response == 'Please update profile or resume to get a better recommendation.':
                return response
            else:
                logging.info(f"Processed response: {response}")
                if output_type == "json":
                    return json.loads(response[response.index("{"):response.index("}")+1])
                else:
                    return response
        except Exception as e:
            logging.error(f"Error in getting response: {e}")
            continue

    raise Exception("Something went wrong. Please try again later.")


def get_jobs(role):
    # Get the jobs
    try:
        # Scrape jobs from multiple sites
        jobs = scrape_jobs(
            site_name=["indeed", "linkedin", "zip_recruiter"],
            search_term=role,
            results_wanted=10,
            hours_old=1440, # (only Linkedin/Indeed is hour specific, others round up to days old)
            country_indeed='USA',  # only needed for indeed / glassdoor
            linkedin_fetch_description=True # get full description and direct job url for linkedin (slower)
        )
        # remove jobs whose description is less than 500 characters
        jobs = jobs[jobs['description'].str.len() > 500]
        logging.info(f"Jobs:{jobs}")

        # Drop duplicate jobs
        jobs = jobs.drop_duplicates("title")
    except Exception as e:
        logging.error(f"Error in scraping jobs: {e}")
        jobs = None
    return jobs


def update_profile(profile_id):

    # Try with chatgpt
    llm = LLM("chatgpt")
    suggestions_prompt = json.load(open("data/prompts.json", "r"))["GET_PROFILE_SUGGESTIONS_PROMPT"]
    prompt = PromptTemplate(
            template=suggestions_prompt,
            input_variables=["PROFILE"]
        )

    atlas_client = AtlasClient()
    profile = atlas_client.find("users", filter={"_id": ObjectId(profile_id)})

    if len(profile) == 0:
        return {}
    
    # get the list of personas from the db
    personas = atlas_client.find("personas")
    # convert it to a dictionary of names and their ids
    personas = {persona["name"]: persona["_id"] for persona in personas}


    profile = profile[0]
    profile = {
        "summary": profile["summary"],
        "name": profile["name"],
        "headline": profile["headline"],
        "location_name": profile["location_name"],
        "education": profile["education"],
        "experience": profile["experience"],
        "courses_taken": profile["courses_taken"],
        "publications": profile["publications"],
        "projects": profile["projects"],
        "certifications": profile["certifications"],
        "patents": profile["patents"],
        "awards": profile["awards"],
    }
    profile = str(profile)

    try:
        response = get_response_from_llm(llm, prompt, inputs={"PROFILE": profile}, output_type="json")
    except Exception as e:
        logging.error(f"Error in getting profile suggestions: {e}")
        response = None
    
    try:
        skills = response["skills"]
        preferred_jobs = response["preferred_jobs"]
        preferred_locations = response["preferred_locations"]
        persona = response["persona"]

        # get the id of the persona
        persona_id = personas[persona]
        
        # update the db
        atlas_client.update("users", filter={"linkedin_profile_id": profile_id}, update={"$set": {"skills": skills, "preferred_jobs": preferred_jobs, "preferred_locations": preferred_locations, "persona": persona_id}})
        return response
    except Exception as e:
        logging.error(f"Error in updating profile: {e}")
        pass

    logging.info("Retrying to get profile suggestions with gemini")
    llm.change_llm_type("gemini")

    try:
        response = get_response_from_llm(llm, prompt, inputs={"PROFILE": profile}, output_type="json")
    except Exception as e:
        logging.error(f"Error in getting profile suggestions: {e}")
        response = None

    try:
        skills = response["skills"]
        preferred_jobs = response["preferred_jobs"]
        preferred_locations = response["preferred_locations"]
        persona = response["persona"]
        # get the id of the persona
        persona_id = personas[persona]
        
        # update the db
        atlas_client.update("users", filter={"linkedin_profile_id": profile_id}, update={"$set": {"skills": skills, "preferred_jobs": preferred_jobs, "preferred_locations": preferred_locations, "persona": persona_id}})
        return response
    except Exception as e:
        logging.error(f"Error in updating profile: {e}")
        pass

    return {}


def get_course_outline(profile_id, job_id, feedback=''):
    # try with chatgpt
    llm = LLM("chatgpt")

    # get the course outline prompt
    course_outline_prompt = json.load(open("data/prompts.json", "r"))["GET_COURSE_OUTLINE_PROMPT"]
    
    # if feedback is provided, add it to the prompt
    if feedback and feedback!="":
        course_outline_prompt += "The user has provided some feedback which needs to be incorporated into the course outline. The feedback is as follows: {FEEDBACK}."

    prompt = PromptTemplate(
            template=course_outline_prompt,
            input_variables=["SKILLS", "PROFILE", "POSITION", "DESCRIPTION", "FEEDBACK"]
        )
    
    atlas_client = AtlasClient()
    profile = atlas_client.find("users", filter={"_id": ObjectId(profile_id)})
    original_job = atlas_client.find("jobsvisiteds", filter={"_id": ObjectId(job_id)})

    if len(original_job) == 0:
        return "Something went wrong. Please try again later."
    
    original_job_id = original_job[0]["job"]
    job = atlas_client.find("jobs", filter={"_id": ObjectId(original_job_id)})

    if len(profile) == 0 or len(job) == 0:
        return "Something went wrong. Please try again later."
    
    profile = profile[0]
    job = job[0]

    profile = {
        "summary": profile["summary"],
        "name": profile["name"],
        "linkedin_profile_id": profile["linkedin_profile_id"],
        "headline": profile["headline"],
        "location_name": profile["location_name"],
        "education": profile["education"],
        "experience": profile["experience"],
        "courses_taken": profile["courses_taken"],
        "publications": profile["publications"],
        "projects": profile["projects"],
        "certifications": profile["certifications"],
        "patents": profile["patents"],
        "awards": profile["awards"],
        "skills": profile["skills"]
    }

    skills = original_job[0]["skill_delta"]
    job_position = job["title"]
    job_description = job["description"]
    profile = str(profile)


    inputs = {"SKILLS": skills, "PROFILE": profile, "POSITION": job_position, "DESCRIPTION": job_description}
    output_type = "string"
    
    try:
        response = get_response_from_llm(llm, prompt, inputs, output_type)
        
        if response == 'Please update profile or resume to get a better recommendation.':
            return response
    
        atlas_client.update("jobsvisiteds", filter={"_id": ObjectId(job_id)}, update={"$set": {"course_outline": response}})
        return response
    except Exception as e:
        logging.error(f"Error in getting course outline: {e}")
        response = None

    
    logging.info("Retrying to get course outline with gemini")
    llm.change_llm_type("gemini")

    try:
        response = get_response_from_llm(llm, prompt, inputs, output_type)
        
        if response == 'Please update profile or resume to get a better recommendation.':
            return response
        
        atlas_client.update("jobsvisiteds", filter={"_id": ObjectId(job_id)}, update={"$set": {"course_outline": response}})
        return response
    except Exception as e:
        logging.error(f"Error in getting course outline: {e}")
        response = None
    
    return "Something went wrong. Please try again later."
    

def generate_cover_letter(profile_id, job_id):
    llm = LLM("chatgpt")
    cover_letter_prompt = json.load(open("data/prompts.json", "r"))["GENERATE_COVER_LETTER_PROMPT"]
    prompt = PromptTemplate(
            template=cover_letter_prompt,
            input_variables=["PROFILE", "JOB_DESCRIPTION"]
        )
    
    atlas_client = AtlasClient()
    
    profile = atlas_client.find("users", filter={"_id": ObjectId(profile_id)})
    original_job = atlas_client.find("jobsvisiteds", filter={"_id": ObjectId(job_id)})

    
    if len(original_job) == 0:
        return "Something went wrong. Please try again later."
    
    original_job_id = original_job[0]["job"]
    job = atlas_client.find("jobs", filter={"_id": ObjectId(original_job_id)})
    

    if len(profile) == 0 or len(job) == 0:
        return "Something went wrong. Please try again later."
    
    profile = profile[0]
    job = job[0]

    profile = {
        "summary": profile["summary"],
        "name": profile["name"],
        "linkedin_profile_id": profile["linkedin_profile_id"],
        "headline": profile["headline"],
        "location_name": profile["location_name"],
        "education": profile["education"],
        "experience": profile["experience"],
        "courses_taken": profile["courses_taken"],
        "publications": profile["publications"],
        "projects": profile["projects"],
        "certifications": profile["certifications"],
        "patents": profile["patents"],
        "awards": profile["awards"],
        "skills": profile["skills"]
    }

    job_position = job["title"]
    profile = str(profile)
    job_description = job_position+"\n\n"+job["description"]

    try:
        response = get_response_from_llm(llm, prompt, inputs={"PROFILE": profile, "JOB_DESCRIPTION": job_description}, output_type="string")
        if response == 'Please update profile or resume to get a better recommendation.':
            return response
        
        # update the cover letter in the jobsvisited
        atlas_client.update("jobsvisiteds", filter={"_id": ObjectId(job_id)}, update={"$set": {"cover_letter": response}})
        return response
    except Exception as e:
        logging.error(f"Error in generating cover letter: {e}")
        response = None

   

    logging.info("Retrying to generate cover letter with gemini")
    llm.change_llm_type("gemini")
    
    
    try:
        response = get_response_from_llm(llm, prompt, inputs={"PROFILE": profile, "JOB_DESCRIPTION": job_description}, output_type="string")

        if response == 'Please update profile or resume to get a better recommendation.':
            return response   

        # update the cover letter in the jobsvisited
        atlas_client.update("jobsvisiteds", filter={"_id": ObjectId(job_id)}, update={"$set": {"cover_letter": response}})
        return response
    
    except Exception as e:
        logging.error(f"Error in generating cover letter: {e}")
        response = None

    
    return "Something went wrong. Please try again later."


def get_skill_match_score(profile_id, job_id):
    llm = LLM("chatgpt")
    skill_match_prompt = json.load(open("data/prompts.json", "r"))["SKILL_MATCH_SCORE_PROMPT"]
    prompt = PromptTemplate(
            template=skill_match_prompt,
            input_variables=["PROFILE", "JOB_DESCRIPTION"]
        )
    
    print(profile_id, job_id)
    

    atlas_client = AtlasClient()
    profile = atlas_client.find("users", filter={"_id": ObjectId(profile_id)})
    job = atlas_client.find("jobsvisiteds", filter={"_id": ObjectId(job_id)})


    


    if len(profile) == 0 or len(job) == 0:
        return {
            "profile_skills": [],
            "job_description_required_skills": [],
            "overlapped_skills": [],
            "skills_to_be_learned": [],
            "match_score": 0
        }
    
    profile = profile[0]
    job = job[0]


    # if job is already present in user's visited jobs collection, return the skill match score
    if "skills_in_profile" in job and "skills_in_job" in job and "skill_delta" in job and "skill_match_score" in job and job["skills_in_profile"]!=[] and job["skills_in_job"]!=[] and job["skill_delta"]!=[] and job["skill_match_score"]!=0:
        return {
            "profile_skills": job["skills_in_profile"],
            "job_description_required_skills": job["skills_in_job"],
            "overlapped_skills": job["skills_in_job"],
            "skills_to_be_learned": job["skill_delta"],
            "match_score": job["skill_match_score"]
        }

    profile = {
        "summary": profile["summary"],
        "name": profile["name"],
        "headline": profile["headline"],
        "location_name": profile["location_name"],
        "education": profile["education"],
        "experience": profile["experience"],
        "courses_taken": profile["courses_taken"],
        "publications": profile["publications"],
        "projects": profile["projects"],
        "certifications": profile["certifications"],
        "patents": profile["patents"],
        "awards": profile["awards"],
        "skills": profile["skills"]
    }

    # fill in the job
    original_job_id  = job["job"]
    job = atlas_client.find("jobs", filter={"_id": ObjectId(original_job_id)})
    job = job[0]

    

    job_position = job["title"]
    job_description = job_position+"\n\n"+job["description"]
    profile = str(profile)

    try:
        response = get_response_from_llm(llm, prompt, inputs={"PROFILE": profile, "JOB_DESCRIPTION": job_description}, output_type="json")
    except Exception as e:
        logging.error(f"Error in getting skill match score: {e}")
        response = None


    try:
        profile_skills = response['PROFILE_SKILLS']
        job_description_required_skills = response['JOB_DESCRIPTION_REQUIRED_SKILLS']
        overlapped_skills = response['OVERLAPPED_SKILLS']
        skills_to_be_learned = response['SKILLS_TO_BE_LEARNED']

        total_skills = len(job_description_required_skills)
        matched_skills = len(overlapped_skills)
        try:
            match_score = matched_skills / total_skills * 100
        except ZeroDivisionError:
            pass


        # update the jobs visited
        atlas_client.update("jobsvisiteds", 
                            filter={"_id": ObjectId(job_id)},
                            update={"$set": {"skills_in_profile": profile_skills, "skills_in_job": job_description_required_skills, "skill_delta": skills_to_be_learned, "skill_match_score": match_score}})
                            

        response = {
            "profile_skills": profile_skills,
            "job_description_required_skills": job_description_required_skills,
            "overlapped_skills": overlapped_skills,
            "skills_to_be_learned": skills_to_be_learned,
            "match_score": match_score
        }

        return response
    except Exception as e:
        logging.error(f"Error in getting skill match score: {e}")
        pass


    logging.info("Retrying to get skill match score with gemini")
    llm.change_llm_type("gemini")
    
    try:
        response = get_response_from_llm(llm, prompt, inputs={"PROFILE": profile, "JOB_DESCRIPTION": job_description}, output_type="json")
    except Exception as e:
        logging.error(f"Error in getting skill match score: {e}")
        response = None

    try:
        profile_skills = response['PROFILE_SKILLS']
        job_description_required_skills = response['JOB_DESCRIPTION_REQUIRED_SKILLS']
        overlapped_skills = response['OVERLAPPED_SKILLS']
        skills_to_be_learned = response['SKILLS_TO_BE_LEARNED']

        total_skills = len(job_description_required_skills)
        matched_skills = len(overlapped_skills)
        try:
            match_score = matched_skills / total_skills * 100
        except ZeroDivisionError:
            pass

        # update the jobs visiteds collections with the new entry
        atlas_client.update("jobsvisiteds", 
                            filter={"_id": ObjectId(job_id)},
                            update={"$set": {"skills_in_profile": profile_skills, "skills_in_job": job_description_required_skills, "skill_delta": skills_to_be_learned, "skill_match_score": match_score}})
        
        
        response = {
            "profile_skills": profile_skills,
            "job_description_required_skills": job_description_required_skills,
            "overlapped_skills": overlapped_skills,
            "skills_to_be_learned": skills_to_be_learned,
            "match_score": match_score
        }

        return response
    except Exception as e:
        logging.error(f"Error in getting skill match score: {e}")
        pass

    return {
        "profile_skills": [],
        "job_description_required_skills": [],
        "overlapped_skills": [],
        "skills_to_be_learned": [],
        "match_score": 0
    }