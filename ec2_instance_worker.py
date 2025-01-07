import boto3
from botocore.exceptions import ClientError
from ec2_enable_serial_helper import enable_serial_console
from ec2_get_instance_ip_helper import get_instance_ip
from ec2_send_serial_console_public_key import send_serial_console_ssh_public_key
from ec2_send_serial_commands import connect_serial_console

def instance_worker(ec2_client, ec2_instance_connect, args, instance_id, public_key, private_key, serial_console_endpoint, kernel_arguments):
    """Thread worker function to wait for instance to reach 'running' state and execute commands."""
    ssm_client = boto3.client('ssm')

    # Wait for the instance to reach the 'running' state
    waiter = ec2_client.get_waiter('instance_running')
    try:
        print(f"Waiting for instance {instance_id} to enter 'running' state...")
        waiter.wait(InstanceIds=[instance_id])
        print(f"Instance {instance_id} is now running.")
    except ClientError as e:
        print(f"Error waiting for instance {instance_id} to enter 'running' state: {e}")
        return

    # Step 3: Enable serial console access
    enable_serial_console(instance_id)

    # EC2 instance public IP or DNS, replace with your own instance's IP
    if args.debug:
        instance_ip = get_instance_ip(ec2_client, instance_id)

    # Step 5 - send the SSH public key to the instance serial console
    print("Sending SSH public key to the instance serial console...")
    send_serial_console_ssh_public_key(ec2_instance_connect, instance_id, public_key)

    # Step 6 - connect to the serial console and send keystrokes
    print("Connecting to the serial console and sending keystrokes...")
    # Connect to serial console and send keystrokes
    connect_serial_console(serial_console_endpoint, instance_id, private_key, kernel_arguments)
    print("EC2 instance setup completed.")

    # Wait for the instance to reach the 'running' state
    print(f"Waiting for the EC2 instance {instance_id} to reach the stopped state...")
    waiter = ec2_client.get_waiter('instance_stopped')
    try:
        print(f"Waiting for instance {instance_id} to enter 'stopped' state...")
        waiter.wait(InstanceIds=[instance_id])
        print(f"Instance {instance_id} is now stopped.")
    except ClientError as e:
        print(f"Error waiting for instance {instance_id} to enter 'stopped' state: {e}")
        return