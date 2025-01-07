# ec2_fleet_helper.py

import boto3

"""
Example of Launch Template overrides:

                'Overrides': [
                    {
                        'InstanceType': 't3.micro',
                        'AvailabilityZone': 'eu-central-1a',
                        'MaxPrice': '0.05',
                        'WeightedCapacity': 1,
                    },
                    {
                        'InstanceType': 'm5.large',
                        'AvailabilityZone': 'eu-central-1b',
                        'MaxPrice': '0.10',
                        'WeightedCapacity': 1,
                    },
                ],
"""

def create_ec2_fleet(ec2_client, args, launch_template_id, total_capacity, on_demand_capacity, spot_capacity):
    """Create an EC2 fleet using the provided launch template."""

    # Define the EC2 Fleet request configuration
    fleet_config = {
        'TargetCapacitySpecification': {
            'TotalTargetCapacity': total_capacity,
            'OnDemandTargetCapacity': on_demand_capacity,
            'SpotTargetCapacity': spot_capacity,
            'DefaultTargetCapacityType': 'spot',
        },
        'LaunchTemplateConfigs': [
            {
                'LaunchTemplateSpecification': {
                    'LaunchTemplateId': launch_template_id,
                    'Version': '$Latest',
                },
                'Overrides': [],
            },
        ],
        'OnDemandOptions': {
            'AllocationStrategy': 'prioritized'
        },
        'SpotOptions': {
            'AllocationStrategy': 'capacityOptimized',
            'InstanceInterruptionBehavior': 'terminate'
        },
        'Type': 'instant',
    }

    # Make the API call to launch the EC2 Fleet
    response = ec2_client.create_fleet(
        LaunchTemplateConfigs=fleet_config['LaunchTemplateConfigs'],
        TargetCapacitySpecification=fleet_config['TargetCapacitySpecification'],
        SpotOptions=fleet_config['SpotOptions'],
        OnDemandOptions=fleet_config['OnDemandOptions'],
        Type=fleet_config['Type']
    )

    print("EC2 Fleet request created successfully.")
    if args.debug:
        print(response)

    # Extract instance IDs from the fleet response
    instance_ids = []
    for instance in response['Instances']:
        for instance_data in instance['InstanceIds']:
            instance_ids.append(instance_data)

    # Extract fleet ID from the response
    fleet_id = response['FleetId']

    print(f"Fleet ID: {fleet_id}")
    print(f"Instances launched: {instance_ids}")
    return fleet_id, instance_ids

def delete_ec2_fleet(ec2_client, fleet_id):
    """Delete an EC2 fleet."""
    try:
        ec2_client.delete_fleets(
            FleetIds=[fleet_id],
            TerminateInstances=True  # Also terminates the instances in the fleet
        )
        print(f"Fleet {fleet_id} deleted successfully.")
    except Exception as e:
        print(f"Error deleting fleet {fleet_id}: {e}")