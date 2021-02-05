# Overview

This is a tiny project to practice DevOps config mgmt & AWS ASG/EC2/EBS provisioning skills

## How to use this utility

The following sections contain instructions to help operators

### Python dependencies / Poetry installation

Make sure you have Python3.6 installed and, to install Poetry, just follow the instructions from [https://python-poetry.org/docs/#installation](https://python-poetry.org/docs/#installation)

### AWS configuration

Just set up the default `region`, `aws_access_key_id` & `aws_secret_access_key` parameters under your `~/.aws/credentials` file, like this:
```
[default]
aws_access_key_id=<your_access_key_here>
aws_secret_access_key=<your_secret_key_here>
```

And then just run:

```
poetry install
poetry run python mprovisioner/mprovisioner.py
```
