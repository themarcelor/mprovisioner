import boto3
import botocore
from cloud.api import APIHandler
import time
import logging
import os


logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


class AWSAPIHandler(APIHandler):
    """
    API Handler for AWS SDK interactions
    """

    def _get_asg(self, asg_client):
        asg_lookup = asg_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=["MProvisionerASG1",]
        )
        asgs = asg_lookup["AutoScalingGroups"]
        if len(asgs) > 0:
            return asgs[0]
        else:
            return None

    def _delete_existing_resources(self, asg_client, ec2_client):
        """
        Deletes existing resources to keep the automation idempotent
        """
        # TODO: Parameterize another instruction in case the user just wants to skip already-provisioned resources
        try:
            asg_deletion_result = asg_client.delete_auto_scaling_group(
                AutoScalingGroupName="MProvisionerASG1", ForceDelete=True
            )
            log.debug(f"Auto Scaling Group deletion result: {asg_deletion_result}")
        except botocore.exceptions.ClientError as ve:
            log.warn(ve)

        try:
            launch_config_deletion_result = asg_client.delete_launch_configuration(
                LaunchConfigurationName="MProvisionerLC1"
            )
            log.debug(
                f"Launch Configuration deletion result: {launch_config_deletion_result}"
            )
        except botocore.exceptions.ClientError as ve:
            log.warn(ve)

        # Make sure the old MProvisionerASG1 is fully deleted
        for i in range(0, 10):
            lingering_asg = self._get_asg(asg_client)
            if lingering_asg:
                log.info("Still working on the deletion of ASG MProvisionerASG1...")
                time.sleep(10)
            else:
                break

        try:
            sg_deletion_result = ec2_client.delete_security_group(
                GroupName="MProvisionerSG1"
            )
            log.debug(f"Security Group deletion result: {sg_deletion_result}")
        except botocore.exceptions.ClientError as ve:
            log.warn(ve)

    def _find_ami_id(self, ec2_client):
        """
        Identify the most recently-created AMI that matches the specs defined in environments.yaml

        Return:
            the AMI ID
        """
        ami_type = self.environment_config["ami_type"]
        virtualization_type = self.environment_config["virtualization_type"]
        architecture = self.environment_config["architecture"]

        # the following query is equivalent to the CLI command:
        # % aws ec2 describe-images --owners self amazon --filters \
        #    Name=architecture,Values=x86_64 \
        #    Name=root-device-type,Values=ebs \
        #    Name=virtualization-type,Values=hvm \
        #    Name=owner-id,Values= 137112412989\ # This is Amazon's Owner ID
        #    Name=name,Values=\*amzn2\*

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

        return ami_id

    def provision_vms(self):
        """
        Creates EC2 VMs (through an Auto Scaling Group) according to the settings specified in environments.yaml
        """
        log.debug(f"environment configuration: {self.environment_config}")

        session = boto3.Session(profile_name="default")
        default_region = session.region_name
        log.info(f"utilizing default region {default_region}")

        # TODO: This function is too long (could use some refactoring)

        # Creating Boto3 Client objects to provision resources and interact with these services
        ec2_client = boto3.client("ec2", region_name=default_region)
        asg_client = boto3.client("autoscaling", region_name=default_region)

        # users
        user_data_commands = ["#!/usr/bin/env bash"]
        for u in self.environment_config["users"]:
            ulogin = u["login"]
            usshkey = u["ssh_key"]
            log.debug(f"preparing configuration to add public key from user {ulogin}")
            user_data_commands.append(f"sudo useradd -m {ulogin}")
            user_data_commands.append(f"sudo mkdir /home/{ulogin}/.ssh")
            user_data_commands.append(
                f"sudo sh -c 'sudo echo \"{usshkey}\" > /home/{ulogin}/.ssh/authorized_keys'"
            )

        # disks
        # TODO: Introduce permanent config to /etc/fstab
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
            user_data_commands.append(f"sudo mkdir {dmount}")
            user_data_commands.append(f"sudo mount {ddevice} {dmount}")

            block_device_mappings.append(disk)

        # find AMI ID according to specs
        ami_id = self._find_ami_id(ec2_client)

        # BEGIN -- Idempotent configuration management (delete resources if they already exist)
        self._delete_existing_resources(asg_client, ec2_client)

        # Identify Default VPC (Every AWS account has one default VPC for each AWS Region)
        # TODO: Allow user to specify different VPCs / multiple AZs / Subnets per environment
        vpc_lookup_result = ec2_client.describe_vpcs(
            Filters=[{"Name": "instance-tenancy", "Values": ["default"]}]
        )
        log.debug(f"Looking for the default VPC: {vpc_lookup_result}")
        vpcs = vpc_lookup_result["Vpcs"]
        if len(vpcs) > 0:
            default_vpc_id = vpc_lookup_result["Vpcs"][0]["VpcId"]
        else:
            raise Exception(
                "Could not find a default VPC on region {default_region}! Abort provisioning."
            )

        # Create security group to allow inbound SSH connection
        try:
            security_group_creation_result = ec2_client.create_security_group(
                GroupName="MProvisionerSG1",
                Description="allow inbound SSH traffic",
                VpcId=default_vpc_id,
            )
            security_group_id = security_group_creation_result["GroupId"]
            ec2_client.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=[
                    {
                        "IpProtocol": "tcp",
                        "FromPort": 22,
                        "ToPort": 22,
                        "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                    }
                ],
            )
            log.info("Security Group created successfully!")
        except botocore.exceptions.ClientError as e:
            raise Exception("Could not create security group! Abort provisioning.")

        # Creating a Launch Configuration to be used by the AutoScaling Group
        asg_client.create_launch_configuration(
            LaunchConfigurationName="MProvisionerLC1",
            ImageId=ami_id,
            InstanceType=self.environment_config["instance_type"],
            UserData="\n".join(user_data_commands),
            SecurityGroups=[security_group_id,],
            BlockDeviceMappings=block_device_mappings,
        )
        log.info("Launch Configuration created successfully!")

        # Creating an Auto Scaling Group to control the fleet of EC2s
        asg_client.create_auto_scaling_group(
            AutoScalingGroupName="MProvisionerASG1",
            MinSize=self.environment_config["min_count"],
            MaxSize=self.environment_config["max_count"],
            LaunchConfigurationName="MProvisionerLC1",
            AvailabilityZones=[f"{default_region}a", f"{default_region}b",],
        )
        log.info("Auto Scaling Group created successfully!")

        # TODO: Polling logic to determine when the EC2 instances are fully up and running (completed checks)
        log.info("Waiting for Ec2 instances...")
        time.sleep(15)

        # Find the newly-provisioned ASG, fetch its instances and print ssh instructions to the user
        new_asg = self._get_asg(asg_client)
        log.info(f"Fetching instances from ASG {new_asg}...")
        instance_ids = []
        for ec2_instance in new_asg["Instances"]:
            instance_ids.append(ec2_instance["InstanceId"])

        # Printing ssh instructions
        log.info(f"Use the following commands to ssh to the newly-provisioned VMs:")
        print(
            "ssh -i <private_key_from_your_user> <user>@<ec2_instance_public_ip_address>"
        )
        print("e.g.,")
        for eid in instance_ids:
            ec2_describe_instances_result = ec2_client.describe_instances(
                Filters=[{"Name": "instance-id", "Values": [eid]}]
            )
            ec2_public_dns_name = ec2_describe_instances_result["Reservations"][0][
                "Instances"
            ][0]["PublicDnsName"]
            print(
                "ssh -i user1-ssh-key-file {}@{}".format(
                    self.environment_config["users"][0]["login"], ec2_public_dns_name
                )
            )
