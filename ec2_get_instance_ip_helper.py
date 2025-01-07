def get_instance_ip(ec2_client, instance_id):
    # Get the public IP address of the instance
    print(f"Retrieving public IP for instance {instance_id}...")

    reservations = ec2_client.describe_instances(InstanceIds=[instance_id])['Reservations']

    if len(reservations) > 0:
        instances = reservations[0]['Instances']
        if len(instances) > 0:
            instance = instances[0]
            instance_ip = instance.get('PublicIpAddress', None)  # Get the public IP address if it exists
            if instance_ip:
                print(f"Instance Public IP: {instance_ip}")
                return instance_ip
            else:
                print(f"Instance {instance_id} does not have a public IP address (it may not be assigned yet).")
                return None
    else:
        print(f"No information found for instance {instance_id}.")
        return None