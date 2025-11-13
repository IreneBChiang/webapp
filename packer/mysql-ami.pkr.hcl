packer {
  required_plugins {
    amazon = {
      source  = "github.com/hashicorp/amazon"
      version = ">= 1.2.0"
    }
  }
}

variable "region" {
  type = string
}

variable "demo_account_id" {
  type = string
}

variable "app_artifact" {
  type = string
}

variable "app_port" {
  type    = number
  default = 8080
}

variable "db_name" {
  type    = string
  default = "assignment05"
}

variable "db_user" {
  type    = string
  default = "app_user"
}

variable "db_pass" {
  type      = string
  sensitive = true
  default = "unused"
}

variable "service_name" {
  type    = string
  default = "myapp"
}

# AMI 篩選參數（可改但不用硬寫 ID）
variable "ubuntu_ami_name_pattern" {
  type = string
  # 放寬匹配，避免 Canonical 命名微調時抓不到
  default = "*ubuntu-noble-24.04-amd64-server-*"
}
variable "ubuntu_owner" {
  type    = string
  default = "099720109477" # Canonical
}

source "amazon-ebs" "ubuntu2404" {
  region        = var.region
  ami_name      = "a05-${formatdate("YYYYMMDD-hhmmss", timestamp())}"
  instance_type = "t3.micro" # x86_64 → 搭配 amd64 AMI
  ssh_username  = "ubuntu"
  ami_users     = [var.demo_account_id]

  source_ami_filter {
    filters = {
      name                = var.ubuntu_ami_name_pattern
      root-device-type    = "ebs"
      virtualization-type = "hvm"
      state               = "available"
      # 也可加上 architecture 強化匹配（可留可去）
      architecture = "x86_64"
    }
    owners      = [var.ubuntu_owner]
    most_recent = true
  }

  tags = {
    Project = "csye6225"
    Purpose = "A06"
  }
}

build {
  name    = "fastapi-rds-s3-ami"
  sources = ["source.amazon-ebs.ubuntu2404"]

  provisioner "shell" {
    inline_shebang   = "/usr/bin/env bash"                # 加這行：用 bash
    environment_vars = ["DEBIAN_FRONTEND=noninteractive"] # 避免 apt 卡互動

    inline = [
      "sudo cloud-init status --wait || true",
      "sudo bash -c 'while fuser /var/lib/apt/lists/lock >/dev/null 2>&1; do echo waiting apt lists lock; sleep 5; done'",
      "sudo bash -c 'while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do echo waiting dpkg lock; sleep 5; done'",
      "sudo bash -c 'while fuser /var/lib/apt/daily_lock >/dev/null 2>&1; do echo waiting apt daily; sleep 5; done' || true",
      "sudo apt-get update -y -o Acquire::Retries=5",
      "sudo apt-get install -y unzip python3-venv python3-pip",

      "sudo groupadd -f csye6225 || true",
      "id -u csye6225 >/dev/null 2>&1 || sudo useradd -g csye6225 -s /usr/sbin/nologin -m -d /opt/csye6225 csye6225",
    ]
  }

  provisioner "file" {
    source      = var.app_artifact
    destination = "/tmp/artifact.zip"
  }

  provisioner "shell" {
    inline_shebang   = "/usr/bin/env bash" # 也用 bash
    environment_vars = ["DEBIAN_FRONTEND=noninteractive"]

    inline = [
      "sudo mkdir -p /opt/myapp /etc/myapp",
      "sudo unzip -o /tmp/artifact.zip -d /opt/myapp",
      "sudo chown -R ubuntu:ubuntu /opt/myapp",
      "sudo chmod +x /opt/myapp/start.sh",
      "command -v dos2unix >/dev/null 2>&1 && sudo dos2unix /opt/myapp/start.sh || true",
      "cd /opt/myapp && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt",
      "cat <<ENV | sudo tee /etc/myapp/.env >/dev/null\nAPP_PORT=${var.app_port}\n# DATABASE_URL & S3_BUCKET_NAME will be injected by Terraform user_data on boot\nENV",

      "sudo chown -R csye6225:csye6225 /etc/myapp",

      <<-SVC
      cat <<EOF | sudo tee /etc/systemd/system/${var.service_name}.service >/dev/null
      [Unit]
      Description=FastAPI App
      After=network-online.target
      Wants=network-online.target
      [Service]
      User=csye6225
      Group=csye6225
      EnvironmentFile=/etc/myapp/.env
      WorkingDirectory=/opt/myapp
      ExecStart=/bin/bash -lc \"/opt/myapp/start.sh\"
      StandardOutput=append:/var/log/webapp/app.log
      StandardError=append:/var/log/webapp/app.log
      Restart=on-failure
      RestartSec=5
      [Install]
      WantedBy=multi-user.target
      EOF
      SVC
      ,
      "sudo systemctl daemon-reload",
      "sudo systemctl enable ${var.service_name}"
    ]
  }

  # 安裝 CloudWatch Agent + 準備日誌
  provisioner "shell" {
    inline_shebang   = "/usr/bin/env bash"
    environment_vars = ["DEBIAN_FRONTEND=noninteractive"]

    inline = [
      # 安裝 CloudWatch Agent (Ubuntu)
      "sudo apt-get update -y -o Acquire::Retries=5",
      "if ! command -v amazon-cloudwatch-agent >/dev/null 2>&1; then ",
      # 官方 deb (amd64)
      "wget -q https://amazoncloudwatch-agent.s3.amazonaws.com/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb &&",
      "sudo apt-get install -y ./amazon-cloudwatch-agent.deb;",
      "fi",

      # （可選）先把 nginx 套件裝好，但不下發站台設定；站台設定交給 userdata 用 ${app_port} 產生
      "if ! dpkg -s nginx >/dev/null 2>&1; then sudo apt-get install -y nginx; fi",

      # 建立 webapp 日誌檔，先寫一行，讓 Log Stream 能即時出現
      "sudo install -d -m 0755 /var/log/webapp",
      "sudo touch /var/log/webapp/app.log",
      "sudo chown csye6225:csye6225 /var/log/webapp/app.log",
      "sudo chmod 0664 /var/log/webapp/app.log",
      "echo \"bootstrap cw $(date -u +%FT%TZ)\" | sudo tee -a /var/log/webapp/app.log >/dev/null",

      # 預先建立 agent 設定目錄（JSON 開機時由 userdata 寫入）
      "sudo install -d -m 0755 /opt/aws/amazon-cloudwatch-agent/etc",

      # 啟用服務（不強制啟動，避免 AMI 打包時啟動失敗）
      "sudo systemctl enable amazon-cloudwatch-agent || true"
    ]
  }
}