#!/usr/bin/env bash
# Creates the disposable resources: private S3 bucket, IAM role + instance profile (SSM core + this bucket only), a security group with NO ingress rules, and the EC2 instance.
# Nothing is created before you type CREATE. Every ID is written to $P17_STATE for the cleanup script.
set -euo pipefail
. "$(dirname "$0")/env.sh"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
echo "Account $ACCOUNT, region $AWS_REGION, profile $AWS_PROFILE, run $P17_RUN"
echo "Will create: 1 x $P17_INSTANCE_TYPE, ${P17_VOLUME_GIB} GiB gp3 (encrypted, delete-on-termination), 1 security group (no inbound), 1 IAM role+profile, 1 private S3 bucket."
read -r -p "Type CREATE to incur charges: " ok; [ "$ok" = CREATE ] || { echo aborted; exit 1; }
save() { echo "export $1=$2" >> "$P17_STATE"; export "$1=$2"; }

BUCKET=$(echo "$P17_RUN-$ACCOUNT" | tr 'A-Z_' 'a-z-'); save P17_BUCKET "$BUCKET"
if [ "$AWS_REGION" = us-east-1 ]; then aws s3api create-bucket --bucket "$BUCKET" >/dev/null
else aws s3api create-bucket --bucket "$BUCKET" --create-bucket-configuration LocationConstraint="$AWS_REGION" >/dev/null; fi
aws s3api put-public-access-block --bucket "$BUCKET" --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-tagging --bucket "$BUCKET" --tagging 'TagSet=[{Key=Project,Value=netspout-phase17},{Key=Disposable,Value=true},{Key=splunkit_data_classification,Value=private},{Key=splunkit_environment_type,Value=non-prd}]'

ROLE=$P17_RUN-role; save P17_ROLE "$ROLE"
aws iam create-role --role-name "$ROLE" --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}' --tags Key=Project,Value=netspout-phase17 Key=splunkit_data_classification,Value=private Key=splunkit_environment_type,Value=non-prd >/dev/null
aws iam attach-role-policy --role-name "$ROLE" --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
aws iam put-role-policy --role-name "$ROLE" --policy-name bucket --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"s3:GetObject\",\"s3:PutObject\"],\"Resource\":\"arn:aws:s3:::$BUCKET/*\"},{\"Effect\":\"Allow\",\"Action\":\"s3:ListBucket\",\"Resource\":\"arn:aws:s3:::$BUCKET\"}]}"
aws iam create-instance-profile --instance-profile-name "$ROLE" >/dev/null; save P17_PROFILE "$ROLE"
aws iam add-role-to-instance-profile --instance-profile-name "$ROLE" --role-name "$ROLE"; sleep 15

VPC=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text); [ "$VPC" != None ] || { echo "no default VPC: set one up or edit this script"; exit 1; }
SUBNET=$(aws ec2 describe-subnets --filters Name=vpc-id,Values="$VPC" Name=default-for-az,Values=true --query 'Subnets[0].SubnetId' --output text)
SG=$(aws ec2 create-security-group --group-name "$P17_RUN-sg" --description "NetSpout phase17 disposable: no inbound" --vpc-id "$VPC" --tag-specifications "$(tag security-group)" --query GroupId --output text); save P17_SG "$SG"
AMI=$(aws ssm get-parameter --name /aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id --query Parameter.Value --output text); echo "AMI $AMI (Ubuntu 24.04 amd64)"
IID=$(aws ec2 run-instances --image-id "$AMI" --instance-type "$P17_INSTANCE_TYPE" --subnet-id "$SUBNET" --security-group-ids "$SG" --iam-instance-profile Name="$ROLE" \
  --associate-public-ip-address --instance-initiated-shutdown-behavior terminate --metadata-options HttpTokens=required,HttpEndpoint=enabled,HttpPutResponseHopLimit=1 \
  --block-device-mappings "[{\"DeviceName\":\"/dev/sda1\",\"Ebs\":{\"VolumeSize\":$P17_VOLUME_GIB,\"VolumeType\":\"gp3\",\"DeleteOnTermination\":true,\"Encrypted\":true}}]" \
  --tag-specifications "$(tag instance)" "$(tag volume)" --query 'Instances[0].InstanceId' --output text); save P17_INSTANCE "$IID"
aws ec2 wait instance-status-ok --instance-ids "$IID"
echo "waiting for Session Manager..."; for i in $(seq 1 40); do [ "$(aws ssm describe-instance-information --filters Key=InstanceIds,Values="$IID" --query 'InstanceInformationList[0].PingStatus' --output text)" = Online ] && break; sleep 10; done
aws ssm describe-instance-information --filters Key=InstanceIds,Values="$IID" --query 'InstanceInformationList[0].[PingStatus,PlatformName,PlatformVersion]' --output text
echo "Created. State: $P17_STATE. Inbound rules: $(aws ec2 describe-security-groups --group-ids "$SG" --query 'length(SecurityGroups[0].IpPermissions)' --output text) (must be 0)."
