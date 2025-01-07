def send_serial_console_ssh_public_key(ec2_instance_connect, instance_id, public_key):
    # Construct the AWS CLI command to send the SSH public key to the instance serial console
    response = ec2_instance_connect.send_serial_console_ssh_public_key(
        InstanceId=instance_id,
        SerialPort=0,
        SSHPublicKey=public_key
    )
    print(response)
    return response
