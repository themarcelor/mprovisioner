# Overview

This is a tiny project to practice DevOps config mgmt & AWS ASG/EC2/EBS provisioning skills

## How to use this utility

The following sections contain instructions to help operators

### Python dependencies / Poetry installation

Make sure you have Python3.6 installed and, to install Poetry, just follow the instructions from [https://python-poetry.org/docs/#installation](https://python-poetry.org/docs/#installation)

### AWS configuration

Just set up the `aws_access_key_id` & `aws_secret_access_key` parameters under your `~/.aws/credentials` file, like this:
```
[default]
aws_access_key_id=<your_access_key_here>
aws_secret_access_key=<your_secret_key_here>
```

And the default `region` under `~/.aws/config`. e.g.:
```
[default]
region=us-east-2
```

Please pick the credentials from an user with the appropriate permissions to create the required AWS Resources (Ec2, EBS Volumes, Security Groups, Launch Configuration and Auto Scaling Groups). More information [here](https://aws.amazon.com/iam/features/manage-permissions/).

### Environments configuration and how to enable user access to the VMs

To create an ssh key pair and allow access to your own users, just run `ssh-keygen -f ~/my-user-ssh-key-file -t rsa -b 4096` and replace the public keys found under the `users:` block of the `environments.yaml` (Just copy the contents of your `*.pub` file).

These keys will be automatically added to the EC2 VMs' `/home/{user}/.ssh/authorized_keys` file. Once the VM is up and running, you can just follow the instructions on the console which should provide a command similar to:
```
ssh -i ~/user1-ssh-key-file user1@<public_ip_address_from_the_ec2_vm>
```

## How to run

The commands below will install the dependencies and execute the tool (which should seamlessly identify the AWS credentials placed in `~/.aws/credentials`):

```
poetry install
poetry run python mprovisioner/mprovisioner.py
```

## Unit tests

To execute the unit tests run the command below:
```
poetry run python -u -m unittest discover tests
```
