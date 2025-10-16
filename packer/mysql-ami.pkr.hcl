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
}

variable "service_name" {
  type    = string
  default = "myapp"
}

source "amazon-ebs" "ubuntu2404" {
  region        = var.region
  ami_name      = "a05-${formatdate("YYYYMMDD-hhmmss", timestamp())}"
  instance_type = "t3.micro"
  ssh_username  = "ubuntu"
  ami_users     = [var.demo_account_id]
  source_ami_filter {
    filters = {
      name                = "ubuntu/images/*ubuntu-24.04*"
      root-device-type    = "ebs"
      virtualization-type = "hvm"
    }
    owners      = ["099720109477"]
    most_recent = true
  }

  tags = { Project = "csye6225", Purpose = "A05" }
}

build {
  name    = "mysql-fastapi-ami"
  sources = ["source.amazon-ebs.ubuntu2404"]

  provisioner "shell" {
    inline = [
      "sudo groupadd -f csye6225 || true",
      "id -u csye6225 >/dev/null 2>&1 || sudo useradd -g csye6225 -s /usr/sbin/nologin -m -d /opt/csye6225 csye6225",
      "sudo apt-get update -y",
      "sudo DEBIAN_FRONTEND=noninteractive apt-get install -y unzip python3 python3-venv mysql-server",
      "echo '[mysqld]\nbind-address=127.0.0.1' | sudo tee /etc/mysql/mysql.conf.d/zzz-bindonly.cnf",
      "sudo systemctl enable --now mysql",
      <<-EOT
      sudo mysql -uroot <<SQL
      CREATE DATABASE IF NOT EXISTS ${var.db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
      CREATE USER IF NOT EXISTS '${var.db_user}'@'localhost' IDENTIFIED BY '${var.db_pass}';
      GRANT ALL PRIVILEGES ON ${var.db_name}.* TO '${var.db_user}'@'localhost';
      FLUSH PRIVILEGES;
      SQL
      EOT
    ]
  }

  provisioner "file" {
    source      = var.app_artifact
    destination = "/tmp/artifact.zip"
  }

  provisioner "shell" {
    inline = [
      "sudo mkdir -p /opt/myapp /etc/myapp",
      "sudo unzip -o /tmp/artifact.zip -d /opt/myapp",
      "cd /opt/myapp && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt",
      "cat <<ENV | sudo tee /etc/myapp/.env >/dev/null\nAPP_PORT=${var.app_port}\nAPP_DB_ENGINE=mysql\nAPP_DB_HOST=127.0.0.1\nAPP_DB_PORT=3306\nAPP_DB_NAME=${var.db_name}\nAPP_DB_USER=${var.db_user}\nAPP_DB_PASS=${var.db_pass}\nENV",
      "sudo chown -R csye6225:csye6225 /opt/myapp /etc/myapp",
      <<-SVC
      cat <<EOF | sudo tee /etc/systemd/system/${var.service_name}.service >/dev/null
      [Unit]
      Description=FastAPI App
      After=network.target mysql.service
      Requires=mysql.service
      [Service]
      User=csye6225
      Group=csye6225
      EnvironmentFile=/etc/myapp/.env
      WorkingDirectory=/opt/myapp
      ExecStart=/bin/bash -lc \"/opt/myapp/start.sh\"
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
}
