# Overview

This is a tiny project to practice DevOps config mgmt & AWS ASG/EC2/EBS provisioning skills

## How to use this utility

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
