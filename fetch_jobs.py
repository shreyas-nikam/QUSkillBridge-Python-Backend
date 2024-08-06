"""
This script fetches jobs for each persona in the personas collection and adds them to the jobs collection.

Author: Shreyas Nikam
"""


from jobspy import scrape_jobs
import datetime

from pymongo_client import AtlasClient

       

def get_jobs(role, results_wanted=10):
    # Get the jobs
    try:
        # Scrape jobs from multiple sites
        jobs = scrape_jobs(
            site_name=["indeed", "linkedin", "zip_recruiter"],
            search_term=role,
            results_wanted=results_wanted,
            hours_old=1440, # (only Linkedin/Indeed is hour specific, others round up to days old)
            country_indeed='USA',  # only needed for indeed / glassdoor
            linkedin_fetch_description=True # get full description and direct job url for linkedin (slower)
        )
        # remove jobs whose description is less than 500 characters
        jobs = jobs[jobs['description'].str.len() > 500]

        # Drop duplicate jobs
        jobs = jobs.drop_duplicates("title")

        # Convert date_posted to datetime
        for i in range(len(jobs)):
            try:
                jobs['date_posted'][i] = datetime.datetime.strptime(jobs['date_posted'][i], "%Y-%m-%d")
            except:
                jobs['date_posted'][i] = datetime.datetime.now()
                continue

    except Exception as e:
        jobs = None
    return jobs


def run_fetch_jobs(results_wanted=10):
    # Fetches jobs for each persona in the personas collection

    # Get all the personas
    atlas_client = AtlasClient()
    personas = atlas_client.find("personas")

    # Get jobs for each persona
    for persona in personas:
        
        role, id = persona['name'], persona['_id']
        jobs = get_jobs(role, results_wanted=results_wanted)
        
        # add id to each job
        jobs['persona'] = id
        

        # add jobs to the database
        collection = atlas_client.get_collection("jobs")
        collection.insert_many(jobs.to_dict('records'))
        print(f"Added {len(jobs)} jobs for {role}")

    print("Done fetching jobs")

if __name__ == "__main__":
    run_fetch_jobs()


