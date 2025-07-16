"""Utility script to update the codemeta.json file."""

import datetime
from os.path import dirname, join
import re
import json

project_folder = dirname(dirname(__file__))

with open(join(project_folder, "packages/bsb/pyproject.toml"), "r") as f:
    for line in f.readlines():
        if line.startswith("version = "):
            version = line.split('version = "')[1].rsplit('"')[0]
            break
    else:
        raise Exception("Could not find version in pyproject.toml")

codemeta_file = join(project_folder, "codemeta.json")
with open(codemeta_file, "r+") as f:
    metadata = json.loads(f.read())
    metadata["dateModified"] = str(datetime.datetime.now().date())
    metadata["version"] = version
    metadata["downloadUrl"] = re.sub(
        r"/tags/v(\.?[0-9]+){3}", r"/tags/v" + version, metadata["downloadUrl"]
    )
    metadata["releaseNotes"] = re.sub(
        r"/tag/v(\.?[0-9]+){3}", r"/tag/v" + version, metadata["releaseNotes"]
    )
    f.seek(0)
    json.dump(metadata, f, indent=4)

# print bsb version for release GHA
print(version)
