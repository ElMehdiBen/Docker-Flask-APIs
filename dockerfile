# FROM is used to specify the docker base image to be used
FROM python:3.8
# Below command to update and install additional needed packages
RUN apt-get update && apt-get install -y \
    software-properties-common \
    unzip \
    curl \
    xvfb

# Creating a directory called apis inside the container
RUN mkdir ./apis

# Copying all file from outside folder to inside folder (in our case both are called apis)
COPY ./apis ./apis

# WORKDIR is equivalent to CD in linux, used to move inside the folder to access the files easily 
WORKDIR ./apis

# RUN performs a command execution on CMD, this one below installs Python requirements
RUN pip3 install --no-cache-dir -r requirements.txt

# Runs app.py to start Flask API
CMD [ "python3", "app.py" ]
