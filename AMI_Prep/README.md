# Introduction
The set of steps below has been written for (and tested on) the official Ubuntu 24.04 AMI for AWS EC2. It will almost certainly need customizing for other images, but it hopes that it serves as an example to help you get started.

#  References
- https://aws.amazon.com/blogs/compute/using-ec2-serial-console-to-access-the-grub-menu-and-recover-from-boot-failures/
- https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-serial-console-prerequisites.html

# Step by step
1. Launch an EC2 instance of the desired OS - example completed on Ubuntu 24.04 on Arm64
2. Execute the following to rewrite the grub configuration

```sh
sudo tee /etc/default/grub.d/50-cloudimg-settings.cfg <<EOF
# Cloud Image specific Grub settings for AWS EC2 images
# CLOUD_IMG: This file was created/modified by the Cloud Image build process

# Set the recordfail timeout
GRUB_RECORDFAIL_TIMEOUT=0

# Do not wait on grub prompt
GRUB_TIMEOUT=30
GRUB_TIMEOUT_STYLE=menu

# Set the default commandline
GRUB_CMDLINE_LINUX_DEFAULT="console=tty1 console=ttyS0 nvme_core.io_timeout=4294967295"

# Set the grub console type
GRUB_TERMINAL="console serial"
GRUB_SERIAL_COMMAND="serial --speed 115200"

EOF

sudo update-grub
```

3. Cleanup with a script like:

```sh
#!/bin/bash

# Clean and prepare EC2 instance for AMI creation

echo "Starting cleanup process..."

# 1. Remove SSH host keys
echo "Removing SSH host keys..."
sudo rm -f /etc/ssh/ssh_host_*

# 2. Clear shell history for root and other users
echo "Clearing shell history..."
sudo rm -f /root/.bash_history
if [ -d /home/ubuntu ]; then
    sudo rm -f /home/ubuntu/.bash_history
fi

# 3. Remove log files
echo "Removing log files..."
sudo find /var/log -type f -exec rm -f {} \;

# 4. Remove temporary files
echo "Removing temporary files..."
sudo rm -rf /tmp/*
sudo rm -rf /var/tmp/*

# 5. Clear cloud-init logs and data
echo "Clearing cloud-init data and logs..."
sudo rm -rf /var/lib/cloud/*
sudo rm -f /var/log/cloud-init.log
sudo rm -f /var/log/cloud-init-output.log

# 6. Remove machine ID (it will be regenerated on boot)
echo "Removing machine ID..."
sudo truncate -s 0 /etc/machine-id

# 7. Remove cloud-init instance-specific data
echo "Removing cloud-init instance-specific data..."
sudo rm -rf /var/lib/cloud/instances/*

# 8. Clear package manager cache
echo "Cleaning package manager cache..."
sudo apt clean

# 9. Remove SSH authorized keys
echo "Removing SSH authorized keys..."
if [ -d /home/ubuntu/.ssh ]; then
    sudo rm -f /home/ubuntu/.ssh/authorized_keys
fi

# 10. Optional: Remove network configuration (uncomment if needed)
# echo "Removing network configuration (optional)..."
# sudo rm -f /etc/netplan/*.yaml
# sudo rm -f /etc/network/interfaces.d/50-cloud-init.cfg

# 11. Optional: Modify cloud-init config to regenerate SSH keys (uncomment if needed)
# echo "Configuring cloud-init to regenerate SSH host keys..."
# sudo sed -i 's/^ssh_deletekeys:.*$/ssh_deletekeys: true/' /etc/cloud/cloud.cfg
# sudo sed -i 's/^preserve_hostname:.*$/preserve_hostname: false/' /etc/cloud/cloud.cfg

# 12. Shutdown the instance (optional if you're preparing to create an AMI)
echo "Shutting down the instance..."
sudo shutdown now

echo "Cleanup complete. The instance is ready for AMI creation."

```

4. Now build an AMI from the shut down VM
