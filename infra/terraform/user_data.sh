#!/bin/bash
# User data script for EC2 instance initialization

# Update system
yum update -y

# Install Python 3.9 and pip
yum install -y python3.9 python3-pip git

# Install CloudWatch agent
yum install -y amazon-cloudwatch-agent

# Create application directory
mkdir -p /opt/trading-bot
cd /opt/trading-bot

# Clone repository (you'll need to set up SSH keys or use CodeCommit)
# For now, we'll use a placeholder - update with your actual repo
# git clone https://github.com/yourusername/crypto-bot.git .

# Alternative: Use S3 to deploy code
# aws s3 cp s3://your-bucket/trading-bot/ /opt/trading-bot/ --recursive

# Create virtual environment
python3.9 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create systemd service
cat > /etc/systemd/system/trading-bot.service <<EOF
[Unit]
Description=Trading Bot Service
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/trading-bot
Environment="PATH=/opt/trading-bot/venv/bin"
ExecStart=/opt/trading-bot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable trading-bot
systemctl start trading-bot

# Create log directory
mkdir -p /var/log/trading-bot

# Configure CloudWatch agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json <<EOF
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/opt/trading-bot/trading_bot.log",
            "log_group_name": "/aws/ec2/trading-bot",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s

