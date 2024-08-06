courses = [
    "qu-nist/test",
    "qu-airmf/test",
    "qu-aibdi/test",
    "qu-aedt/test",
    "qu-consu/test",
    "qu-agirm/test",
    "qu-scfaco/test",
    "qu-sgmrm/test",
    "qu-genpro/test",
    "qu-scfaconlp/test",
    "qu-prmst/test",
    "qu-gscrrmf/test",
    "qu-srobom/test",
    "qu-colcpl/test",
    "qu-callaw/test",
    "qu-euaia/test",
]

from s3_file_manager import S3FileManager

s3 = S3FileManager()

for course in courses:
    files = s3.list_files(course)
    try:
        print([file['Key'] for file in files if "Certificate" in file["Key"]][0])
    except IndexError:
        print()
        pass
    print()
