courses = {
    "NIST":"qu-nist/test/retriever",
    "AIRMF":"qu-airmf/test/retriever",
    "AIBDI":"qu-aibdi/test/retriever",
    "AEDT":"qu-aedt/test/retriever",
    "CONSU":"qu-consu/test/retriever",
    "AGIRM":"qu-agirm/test/retriever",
    "SCFACO":"qu-scfaco/test/retriever",
    "SGMRM":"qu-sgmrm/test/retriever",
    "GENPRO":"qu-genpro/test/retriever",
    "SCFACONLP":"qu-scfaconlp/test/retriever",
    "PRMST":"qu-prmst/test/retriever",
    "GSCRRMF":"qu-gscrrmf/test/retriever",
    "SROBOM":"qu-srobom/test/retriever",
    "COLCPL":"qu-colcpl/test/retriever",
    "CALLAW":"qu-callaw/test/retriever",
    "EUAIA":"qu-euaia/test/retriever",
}

from s3_file_manager import S3FileManager
from pathlib import Path
s3 = S3FileManager()

for course in courses:
    files = s3.list_files(course)
    try:
        chatbot_files = [file['Key'] for file in files if "retriever" in file["Key"]]
        # for each file in chatbot_files, download the file in the chatbot folder based on htekey and create teh folders if they are not present
        for file in chatbot_files:
            print(file)
            Path(f"chatbot/{file}").parent.mkdir(parents=True, exist_ok=True)
            # if it is a directory continue
            if file.endswith("/"):
                continue
            s3.download_file(file, f"chatbot/{file}")

    except IndexError:
        print()
        pass
    print()
