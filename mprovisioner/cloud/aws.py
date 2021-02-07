import boto3
from cloud.api import APIHandler
import logging
import os


logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


class AWSAPIHandler(APIHandler):
    """
    API Handler for AWS SDK interactions
    """

    def provision_vms(self):
        """
        Creates EC2 VMs (through an Auto Scaling Group) according to the settings specified in environments.yaml
        """
        log.debug(f"environment configuration: {self.environment_config}")

        ami_type = self.environment_config["ami_type"]
        virtualization_type = self.environment_config["virtualization_type"]
        architecture = self.environment_config["architecture"]

        # TODO: This function is too long
        # the user-data, disks and the ami discovery logic must be moved to separate functions

        # users
        user_data_commands = ["#!/usr/bin/env bash"]
        for u in self.environment_config["users"]:
            ulogin = u["login"]
            usshkey = u["ssh_key"]
            log.debug(f"preparing configuration to add public key from user {ulogin}")
            user_data_commands.append(f"useradd -m {ulogin}")
            user_data_commands.append(
                f'echo "{usshkey}" > /home/{ulogin}/.ssh/authorized_keys'
            )

        # disks
        block_device_mappings = []
        for d in self.environment_config["volumes"]:
            ddevice = d["device"]
            dsize_gb = d["size_gb"]
            dtype = d["type"]
            dmount = d["mount"]

            disk = {
                "DeviceName": ddevice,
                "Ebs": {
                    "VolumeSize": dsize_gb,
                    "VolumeType": "gp2",
                    "DeleteOnTermination": True,
                    "Iops": 100,
                },
            }
            # format disk according to the desired filesystem specified in environments.yaml
            user_data_commands.append(f"sudo mkfs -t {dtype} {ddevice}")

            block_device_mappings.append(disk)

        # the following query is equivalent to the CLI command:
        # % aws ec2 describe-images --owners self amazon --filters \
        #    Name=architecture,Values=x86_64 \
        #    Name=root-device-type,Values=ebs \
        #    Name=virtualization-type,Values=hvm \
        #    Name=owner-id,Values= 137112412989\ # This is Amazon's Owner ID
        #    Name=name,Values=\*amzn2\*
        ec2_client = boto3.client("ec2", region_name="us-east-2")
        amis_search_result = ec2_client.describe_images(
            Filters=[
                {
                    "Name": "architecture",
                    "Values": [self.environment_config["architecture"]],
                },
                {
                    "Name": "root-device-type",
                    "Values": [self.environment_config["root_device_type"]],
                },
                {
                    "Name": "virtualization-type",
                    "Values": [self.environment_config["virtualization_type"]],
                },
                {"Name": "owner-id", "Values": ["137112412989"]},
                {
                    "Name": "name",
                    "Values": ["*" + self.environment_config["ami_type"] + "*"],
                },
            ]
        )

        # pick up the most recent AMI based on CreationDate
        amis = amis_search_result["Images"]
        amis.sort(key=lambda x: x["CreationDate"], reverse=True)

        ami_id = amis[0]["ImageId"]
        log.info(f"Latest AMI found among the search results: {amis[0]}")
        log.debug(f"Selected AMI ID: {ami_id}")

        # Creating a Launch Configuration to be used in an AutoScaling Group
        asg_client = boto3.client("autoscaling", region_name="us-east-2")

        # Idempotent configuration management (delete launch configuration if it already exists)
        # TODO: Parameterize another instruction in case the user just wants to skip already-provisioned resources
        launch_config_deletion_result = asg_client.delete_launch_configuration(
            LaunchConfigurationName="MProvisionerLC1"
        )
        log.debug(
            f"Launch Configuration deletion result: {launch_config_deletion_result}"
        )

        asg_client.create_launch_configuration(
            LaunchConfigurationName="MProvisionerLC1",
            ImageId=ami_id,
            InstanceType=self.environment_config["instance_type"],
            UserData="\n".join(user_data_commands),
            BlockDeviceMappings=block_device_mappings,
        )

        # Creating an Auto Scaling Group to control the fleet of EC2s
        asg_client.create_auto_scaling_group(
            AutoScalingGroupName="MProvisionerASG1",
            MinSize=self.environment_config["min_count"],
            MaxSize=self.environment_config["max_count"],
            LaunchConfigurationName="MProvisionerLC1",
            AvailabilityZones=["us-east-2a", "us-east-2b",],
        )

        asg_dict = asg_client.describe_auto_scaling_groups()
        for asg in asg_dict["AutoScalingGroups"]:
            print(asg["AutoScalingGroupName"])
