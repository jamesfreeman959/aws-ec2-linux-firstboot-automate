# aws-ec2-linux-firstboot-automate
A set of proof of concept scripts to enable modification of kernel parameters on first boot of an AWS EC2 instance

# Introduction
These scripts are very much a proof of concept - although they have been tested and demonstrated to work, there is a lot of scope for improvement and customization. The goals of this code are to demonstrate how you can launch an AWS EC2 instance, specify a unique set of kernel parameters, run a script via the `userdata` in the EC2 launch, and then shut down the instance after collecting the results from the run into an S3 bucket.

# WARNING!!!
If you run these scripts on your AWS account, you will almost certainly incur charges! It may be possible to experiment within the Free Tier if your account is eligible, but please exercise caution when running these scripts.

# AMI Preparation
Before you can test the automation code, there's one hurdle we must overcome first - most EC2 images (that is to say, AMI's) do not have the `grub` boot menu enabled. This is a sensible design choice - the images are designed to run headless so there is little point to most people in incurring an additional (billable) delay in waiting for the `grub` boot menu to time out. 

For this code to work, you will need to prepare an AMI with the `grub` menu enabled. The methods for doing this will vary depending on the operating system you choose - some example code for building an AMI based on Ubuntu Server 24.04 can be found in the [AMI_Prep](AMI_Prep) directory.

# Boot automation
Once you have built your AMI, you are now in a position to run the code. To get it up and running, you will need to ensure you have Python 3.9 or later installed, and the modules listed in `requirements.txt`. Set up your Python environment as you prefer, then:

1. Edit the `userdata-script.sh` to perform the operations you want **after** the EC2 instance has booted for the first time. You will find the file in this repository contains some example code, but it will not work as is and you will need to at least set the S3 bucket to one that you own.
2. Copy `config.yaml.example` to `config.yaml` and edit the parameters for your environment - familiarity with AWS will be required to set the values in this file, but in brief, the following configuration must be set:
   1. `ami_id`: The ID of the AMI you built in the AMI Preparation step.
   2. `instance_type`: The instance type you want to launch - for example `t4g.nano`
   3. `key_name`: The private key name that should be applied to the EC2 instance on creation - you must create this in AWS first
   4. `security_group_ids`: A list of the Security Groups you want applied to the EC2 instance - again you must create these first in AWS
   5. `subnet_id`: The subnet ID from your VPC that you want to launch the AWS instance into
   6. `aws_profile`: The name of your AWS profile in your local shell - created (for example) using: `aws configure --profile my-aws-profile`
   7. `serial_console_endpoint`: The serial console endpoint for your chosen EC2 region, as listed here: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-to-serial-console.html#sc-endpoints-and-fingerprints
   8. `private_key_file_path`: A path to the private key that will be used for serial console transactions - this file can be ephemeral and should not be the same as your `key_name`
   9. `kernel_arguments`: A set of parameters to be appended to the kernel arguments prior to boot in grub

Once you have completed this, you are ready to run `automate.py`. There are a limited number of command line options supported, but it should work without specifying any as defaults are set.

# Customizing
This code has been used successfully in a proof of concept, and you are encouraged to read the code to learn how it work. In particular, pay attention to `ec2_send_serial_commands.py` - this code interacts with the grub boot menu on the serial console remotely - however at present it is very simple and does not do any screen scraping - it simply mimmicks the user sending a series of keystrokes. Any changes to the order or structure of the grub menu would result in the code failing, and in addition there is not yet any error trapping or handling.

These are all left as opportunities for others to build on, and it is hoped that this code serves as a building block to help others get started and demonstrate how to interact with the serial console on AWS EC2 instances remotely in a programmatic manner.