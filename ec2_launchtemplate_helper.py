# ec2_fleet_helper.py

import base64
from botocore.exceptions import ClientError

def create_launch_template(ec2_client, template_name, ami_id, instance_type, key_name, security_group_ids, subnet_id, iam_instance_profile_arn, script_content):

    # Check if a launch template with the given name already exists
    try:
        existing_template = ec2_client.describe_launch_templates(
            LaunchTemplateNames=[template_name]
        )
        if existing_template['LaunchTemplates']:
            # If template exists, return its ID
            launch_template_id = existing_template['LaunchTemplates'][0]['LaunchTemplateId']
            print(f"Launch Template '{template_name}' already exists. LaunchTemplateId: {launch_template_id}")
            return launch_template_id
    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidLaunchTemplateName.NotFoundException':
            # If the template is not found, we'll create it
            print(f"Launch Template '{template_name}' not found. Proceeding to create a new one.")
        else:
            # Handle other possible exceptions
            print(f"Unexpected error occurred: {e}")
            raise

    # Convert the shell script to base64 format
    user_data = base64.b64encode(script_content.encode('utf-8')).decode('utf-8')

    # Define the launch template configuration
    launch_template_config = {
        'LaunchTemplateName': template_name,
        'VersionDescription': 'Initial version',
        'LaunchTemplateData': {
            'ImageId': ami_id,
            'InstanceType': instance_type,
            'KeyName': key_name,
            'IamInstanceProfile': {
                'Arn': iam_instance_profile_arn
            },
            "NetworkInterfaces": [{
                "AssociatePublicIpAddress": True,
                "DeviceIndex": 0,
                "Ipv6AddressCount": 0,
                "SubnetId": subnet_id,
                'Groups': security_group_ids
            }],
            'BlockDeviceMappings': [
                {
                    'DeviceName': '/dev/sda1',
                    'Ebs': {
                        'VolumeSize': 8,
                        'VolumeType': 'gp3',
                        'DeleteOnTermination': True
                    }
                }
            ],
            'UserData': user_data,
            'TagSpecifications': [
                {
                    'ResourceType': 'instance',
                    'Tags': [{'Key': 'Name', 'Value': template_name + "_instance"}]
                }
            ]
        }
    }

    # Make the API call to create the launch template
    response = ec2_client.create_launch_template(
        LaunchTemplateName=launch_template_config['LaunchTemplateName'],
        VersionDescription=launch_template_config['VersionDescription'],
        LaunchTemplateData=launch_template_config['LaunchTemplateData']
    )

    # Return the Launch Template ID
    launch_template_id = response['LaunchTemplate']['LaunchTemplateId']
    print(f"Launch Template Created: {launch_template_id}")
    return launch_template_id

def delete_launch_template(ec2_client, launch_template_id):
    """Delete the launch template."""
    try:
        ec2_client.delete_launch_template(
            LaunchTemplateId=launch_template_id
        )
        print(f"Launch Template {launch_template_id} deleted successfully.")
    except Exception as e:
        print(f"Error deleting launch template {launch_template_id}: {e}")