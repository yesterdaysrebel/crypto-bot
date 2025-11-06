#!/bin/bash
# User data script for EC2 instance initialization

# Detect OS and package manager
if command -v dnf &> /dev/null; then
  # Amazon Linux 2023 uses dnf
  PKG_MANAGER=dnf
  UPDATE_CMD="dnf update -y"
  INSTALL_CMD="dnf install -y"
elif command -v yum &> /dev/null; then
  # Amazon Linux 2 uses yum
  PKG_MANAGER=yum
  UPDATE_CMD="yum update -y"
  INSTALL_CMD="yum install -y"
else
  echo "ERROR: No supported package manager found"
  exit 1
fi

# Update system
$UPDATE_CMD

# Install Python 3.9 and pip
if command -v amazon-linux-extras &> /dev/null; then
  # Amazon Linux 2 - use Amazon Linux Extras
  echo "Installing Python 3.9 on Amazon Linux 2..."
  amazon-linux-extras enable python3.9
  $PKG_MANAGER clean metadata
  $INSTALL_CMD python3.9 python3.9-pip git
else
  # Amazon Linux 2023 or other - Python 3.9+ should be available by default
  echo "Installing Python 3.9 on Amazon Linux 2023..."
  $INSTALL_CMD python3.9 python3.9-pip git || $INSTALL_CMD python3 python3-pip git
fi

# Install CloudWatch agent
$INSTALL_CMD amazon-cloudwatch-agent

# Create application directory
mkdir -p /opt/trading-bot
cd /opt/trading-bot

# Clone repository (you'll need to set up SSH keys or use CodeCommit)
# For now, we'll use a placeholder - update with your actual repo
# git clone https://github.com/yourusername/crypto-bot.git .

# Alternative: Use S3 to deploy code
# aws s3 cp s3://your-bucket/trading-bot/ /opt/trading-bot/ --recursive

# Determine Python command
if command -v python3.9 &> /dev/null; then
  PYTHON_CMD=python3.9
elif command -v python3 &> /dev/null; then
  # Check if python3 is 3.9+
  PYTHON3_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
  PYTHON3_MAJOR=$(echo $PYTHON3_VERSION | cut -d. -f1)
  PYTHON3_MINOR=$(echo $PYTHON3_VERSION | cut -d. -f2)
  if [ "$PYTHON3_MAJOR" -eq 3 ] && [ "$PYTHON3_MINOR" -ge 9 ]; then
    PYTHON_CMD=python3
    # Create symlink for consistency
    ln -sf $(which python3) /usr/local/bin/python3.9 2>/dev/null || true
  else
    PYTHON_CMD=python3
    echo "WARNING: Python version is $PYTHON3_VERSION, but 3.9+ is recommended"
  fi
else
  echo "ERROR: Python 3 not found"
  exit 1
fi

# Create virtual environment
$PYTHON_CMD -m venv venv
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

