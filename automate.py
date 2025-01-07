# Important!!!
#
# This script uses both boto3 - it assumes you have configured a suitable profile in the shell - for example:
# $ aws configure --profile my-aws-profile                                                                                                                                        ─╯
# AWS Access Key ID [None]: xxxxx
# AWS Secret Access Key [None]: xxxxxx
# Default region name [None]: eu-central-1
# Default output format [None]:

import boto3
import paramiko
import io
import yaml
import argparse
import os
import signal
import sys
from ec2_launchtemplate_helper import create_launch_template, delete_launch_template
from ec2_fleet_helper import create_ec2_fleet, delete_ec2_fleet
from ec2_enable_serial_helper import enable_serial_console
from ec2_instance_worker import instance_worker
from ec2_get_instance_ip_helper import get_instance_ip
from ec2_send_serial_console_public_key import send_serial_console_ssh_public_key
from ec2_send_serial_commands import connect_serial_console
import threading

# Placeholder variables for launch template and fleet IDs
fleet_id = None
launch_template_id = None

def load_config(filename):
    with open(filename, 'r') as config_file:
        config = yaml.safe_load(config_file)
    return config

def load_userdata(filename):
    with open(filename, 'r') as userdata_file:
        userdata = userdata_file.read()
    return userdata

def signal_handler(sig, frame):
    """Handle Ctrl+C (SIGINT) to ensure cleanup."""
    print("\nCtrl+C pressed. Cleaning up...")
    cleanup_resources()
    sys.exit(0)

def cleanup_resources(ec2_client):
    """Cleanup EC2 Fleet and Launch Template if they were created."""
    if fleet_id:
        print(f"Cleaning up Fleet {fleet_id}...")
        delete_ec2_fleet(ec2_client, fleet_id)
    if launch_template_id:
        print(f"Cleaning up Laucnh Template {launch_template_id}...")
        delete_launch_template(ec2_client, launch_template_id)

def launch_ec2_instance(ec2_client, ami_id, instance_type, key_name, security_group_ids, subnet_id):
    # Launch EC2 instance
    print("Launching EC2 instance...")
    response = ec2_client.run_instances(
        ImageId=ami_id,
        InstanceType=instance_type,
        KeyName=key_name,
        SecurityGroupIds=security_group_ids,
        SubnetId=subnet_id,
        MaxCount=1,
        MinCount=1,
        InstanceInitiatedShutdownBehavior='stop',
        DisableApiTermination=False
    )

    instance_id = response['Instances'][0]['InstanceId']
    print(f"Instance launched with ID: {instance_id}")
    return instance_id


def generate_ssh_key_pair(args, private_key_file_path):
    # Create an RSA key object
    private_key = paramiko.RSAKey.generate(2048)

    # Store private key in memory (PEM format)
    private_key_file = io.StringIO()
    private_key.write_private_key(private_key_file)
    private_key_pem = private_key_file.getvalue()

    # Generate public key (OpenSSH format)
    public_key = f"{private_key.get_name()} {private_key.get_base64()}"

    # Print the keys
    if args.debug:
        print("Private Key (PEM):\n", private_key)
        print("Public Key (OpenSSH):\n", public_key)

    # Write the private key to a file
    if args.debug:
        with open(private_key_file_path, 'w') as private_key_file:
            private_key_file.write(str(private_key))


    return private_key_pem, public_key

def fleet_main():
    ec2_client = None
    global fleet_id, launch_template_id

    # Set up argument parser
    parser = argparse.ArgumentParser(description="EC2 instance configuration and launcher script.")

    # Option to specify the config file (default is config.yaml)
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to the configuration YAML file. Default is "config.yaml".'
    )

    parser.add_argument(
        '--userdata',
        type=str,
        default='userdata-script.sh',
        help='UserData script to run via Launch Template. Default is "userdata-script.sh".'
    )

    # Option to enable debug mode
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode to perform additional actions.'
    )

    parser.add_argument(
        '--keep',
        action='store_true',
        help='Keep the EC2 instances, Fleet and Launch Template on script exit'
    )

    # Parse the command-line arguments
    args = parser.parse_args()

    try:

        # Load configuration from the YAML file (default or specified)
        config_file = args.config
        if not os.path.exists(config_file):
            print(f"Error: Configuration file {config_file} not found!")
            return

        config = load_config(config_file)

        userdata_script = args.userdata
        if not os.path.exists(userdata_script):
            print(f"Error: Userdata script {userdata_script} not found!")
            return
        elif args.debug:
            print(f"Using Userdata script: {userdata_script}")

        userdata = load_userdata(userdata_script)

        ami_id = config['ami_id']
        instance_type = config['instance_type']
        key_name = config['key_name']
        security_group_ids = config['security_group_ids']
        subnet_id = config['subnet_id']
        # Use config.get to prevent exceptions if an optional dictionary element does not exist
        aws_profile = config.get('aws_profile')

        # Serial Console endpoint, as documented here: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-to-serial-console.html#sc-endpoints-and-fingerprints
        serial_console_endpoint = config['serial_console_endpoint']
        # SSH username and key path (replace with your key and username)
        private_key_file_path = config['private_key_file_path']
        # Kernel command line arguments to pass
        # isolcpus=1,2,3 will (on a 4 core system) mean that commands are scheduled only on core 0
        kernel_arguments = config['kernel_arguments']

        # Launch template specifics
        # Launch template name
        template_name = config['launch_template_name']
        iam_instance_profile_arn = config['iam_instance_profile_arn']

        # Fleet specifics
        total_capacity = config['total_capacity']
        on_demand_capacity = config['on_demand_capacity']
        spot_capacity = config['spot_capacity']

        # Debug mode actions
        if args.debug:
            print("Debug Mode Activated")
            print("Loaded configuration:")
            print(f"AMI ID: {ami_id}")
            print(f"Instance Type: {instance_type}")
            print(f"Key Name: {key_name}")
            print(f"Security Group IDs: {security_group_ids}")
            print(f"Subnet ID: {subnet_id}")
            print(f"AWS Profile: {aws_profile}")
            print(f"Serial Console Endpoint: {serial_console_endpoint}")
            print(f"Private Key File Path: {private_key_file_path}")
            print(f"Kernel Arguments: {kernel_arguments}")
            print(f"Launch template name: {template_name}")
            print(f"IAM Instance Profile ARN: {iam_instance_profile_arn}")
            print(f"Total Fleet Capacity: {total_capacity}")
            print(f"On Demand Capacity: {on_demand_capacity}")
            print(f"Spot Capacity: {spot_capacity}")

        # Initialize a session using the specified profile
        session = boto3.Session(profile_name=aws_profile)

        # Initialize the EC2 client
        ec2_client = session.client('ec2')
        ec2_instance_connect = session.client('ec2-instance-connect')

        # Create the Launch Template if it doesn't already exist
        # Create a launch template
        launch_template_id = create_launch_template(
            ec2_client,
            template_name,
            ami_id,
            instance_type,
            key_name,
            security_group_ids,
            subnet_id,
            iam_instance_profile_arn,
            userdata
        )

        # Create an EC2 Fleet request using the created (or existing) launch template
        fleet_id, instance_ids = create_ec2_fleet(ec2_client, args, launch_template_id, total_capacity, on_demand_capacity, spot_capacity)

        # Generate a temporary SSH key pair
        print("Generating temporary SSH key pair...")
        private_key, public_key = generate_ssh_key_pair(args, private_key_file_path)

        threads = []
        for instance_id in instance_ids:
            thread = threading.Thread(target=instance_worker, args=(ec2_client, ec2_instance_connect, args, instance_id, public_key, private_key, serial_console_endpoint, kernel_arguments))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        print("All operations completed.")
    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # Cleanup the fleet and launch template after execution
        if ec2_client is not None and not args.keep:
            cleanup_resources(ec2_client)

def instance_main():
    global fleet_id, launch_template_id
    # Set up argument parser
    parser = argparse.ArgumentParser(description="EC2 instance configuration and launcher script.")

    # Option to specify the config file (default is config.yaml)
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to the configuration YAML file. Default is "config.yaml".'
    )

    # Option to enable debug mode
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode to perform additional actions.'
    )

    # Parse the command-line arguments
    args = parser.parse_args()

    # Load configuration from the YAML file (default or specified)
    config_file = args.config
    if not os.path.exists(config_file):
        print(f"Error: Configuration file {config_file} not found!")
        return

    config = load_config(config_file)

    ami_id = config['ami_id']
    instance_type = config['instance_type']
    key_name = config['key_name']
    security_group_ids = config['security_group_ids']
    subnet_id = config['subnet_id']
    aws_profile = config['aws_profile']
    # Serial Console endpoint, as documented here: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-to-serial-console.html#sc-endpoints-and-fingerprints
    serial_console_endpoint = config['serial_console_endpoint']
    # SSH username and key path (replace with your key and username)
    private_key_file_path = config['private_key_file_path']
    # Kernel command line arguments to pass
    # isolcpus=1,2,3 will (on a 4 core system) mean that commands are scheduled only on core 0
    kernel_arguments = config['kernel_arguments']

    # Debug mode actions
    if args.debug:
        print("Debug Mode Activated")
        print("Loaded configuration:")
        print(f"AMI ID: {ami_id}")
        print(f"Instance Type: {instance_type}")
        print(f"Key Name: {key_name}")
        print(f"Security Group IDs: {security_group_ids}")
        print(f"Subnet ID: {subnet_id}")
        print(f"AWS Profile: {aws_profile}")
        print(f"Serial Console Endpoint: {serial_console_endpoint}")
        print(f"Private Key File Path: {private_key_file_path}")
        print(f"Kernel Arguments: {kernel_arguments}")

    # Initialize a session using the specified profile
    session = boto3.Session(profile_name=aws_profile)

    # Initialize the EC2 client
    ec2_client = session.client('ec2')
    ec2_instance_connect = session.client('ec2-instance-connect')

    # Step 1: Launch EC2 instance
    instance_id = launch_ec2_instance(ec2_client, ami_id, instance_type, key_name, security_group_ids, subnet_id)

    # Step 2: Wait for the instance to be in the 'running' state
    print("Waiting for instance to enter 'running' state...")
    waiter = ec2_client.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instance_id])
    print(f"Instance {instance_id} is running.")

    # Step 3: Enable serial console access
    enable_serial_console(instance_id)

    # EC2 instance public IP or DNS, replace with your own instance's IP
    if args.debug:
        instance_ip = get_instance_ip(ec2_client, instance_id)

    # Step 4 - generate a temporary SSH key pair
    print("Generating temporary SSH key pair...")
    private_key, public_key = generate_ssh_key_pair(args, private_key_file_path)

    # Step 5 - send the SSH public key to the instance serial console
    print("Sending SSH public key to the instance serial console...")
    send_serial_console_ssh_public_key(ec2_instance_connect, instance_id, public_key)

    # Step 6 - connect to the serial console and send keystrokes
    print("Connecting to the serial console and sending keystrokes...")
    # Connect to serial console and send keystrokes
    connect_serial_console(serial_console_endpoint, instance_id, private_key, kernel_arguments)
    print("EC2 instance setup completed.")

if __name__ == "__main__":
    fleet_main()
