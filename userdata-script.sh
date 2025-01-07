#!/bin/sh

S3_BUCKET=my-bucket-name

# This script assumes the presence of a policy that allows access to the required S3 bucket is attached to the EC2 instance
apt update
apt -y install unzip
curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "/tmp/awscliv2.zip"
unzip /tmp/awscliv2.zip -d /tmp
/tmp/aws/install

aws s3 cp s3://${S3_BUCKET}/tools/code.zip /tmp
unzip /tmp/code.zip -d /tmp

TOKEN=`curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600"`
INSTANCETYPE=`curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-type`
INSTANCEID=`curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id`

echo "Aws:" >> instance_info.yml
echo "  InstanceType: ${INSTANCETYPE}" >> instance_info.yml
echo "  CmdLine: $(cat /proc/cmdline)" >> instance_info.yml

aws s3 cp results_all.yml s3://${S3_BUCKET}/results/${INSTANCEID}_${INSTANCETYPE}_$(date +%Y%m%d_%H%M%S).yml

shutdown -h now