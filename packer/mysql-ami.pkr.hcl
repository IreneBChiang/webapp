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

variable "ubuntu_ami_name_pattern" {
  type    = string
  default = "*ubuntu-noble-24.04-amd64-server-*"
}

source "amazon-ebs" "ubuntu2404" {
  region        = var.region
  ami_name      = "a05-${formatdate("YYYYMMDD-hhmmss", timestamp())}"
  instance_type = "t3.micro"
  ssh_username  = "ubuntu"
  ami_users     = [var.demo_account_id]

  source_ami_filter {
    filters = {
      name                = var.ubuntu_ami_name_pattern
      root-device-type    = "ebs"
      virtualization-type = "hvm"
      state               = "available"
    }
    owners      = ["099720109477"] # Canonical
    most_recent = true
  }

  tags = {
    Project = "csye6225"
    Purpose = "A05"
  }
}

build {
  name    = "mysql-fastapi-ami"
  sources = ["source.amazon-ebs.ubuntu2404"]

  # ---- 基礎與 MySQL 安裝／初始化 ----
  provisioner "shell" {
    inline_shebang = "/bin/bash -euxo pipefail"
    # 讓 packer 先 chmod +x，再直接把檔案當可執行檔跑；避免用 -c 字串
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"

    inline = [
      # 基本環境
      "apt-get update -y",
      "DEBIAN_FRONTEND=noninteractive apt-get install -y apt-utils unzip python3 python3-venv mysql-server",
      "groupadd -f csye6225 || true",
      "id -u csye6225 >/dev/null 2>&1 || useradd -g csye6225 -s /usr/sbin/nologin -m -d /opt/csye6225 csye6225",

      # MySQL 設定：只綁 127.0.0.1
      "printf '[mysqld]\\nbind-address=127.0.0.1\\n' > /etc/mysql/mysql.conf.d/zzz-bindonly.cnf",
      "systemctl enable --now mysql",

      # 初始化 DB / 使用者（用 -e 一次性執行，避免 heredoc 造成 GA/bash 語法誤判）
      "mysql -uroot -e \"CREATE DATABASE IF NOT EXISTS ${var.db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE USER IF NOT EXISTS '${var.db_user}'@'localhost' IDENTIFIED BY '${var.db_pass}'; GRANT ALL PRIVILEGES ON ${var.db_name}.* TO '${var.db_user}'@'localhost'; FLUSH PRIVILEGES;\""
    ]
  }

  # 傳入打包好的應用程式 zip
  provisioner "file" {
    source      = var.app_artifact
    destination = "/tmp/artifact.zip"
  }

  # 佈署 App 與 systemd service
  provisioner "shell" {
    inline_shebang  = "/bin/bash -euxo pipefail"
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"

    inline = [
      # 展開、建 venv、安裝套件
      "mkdir -p /opt/myapp /etc/myapp",
      "unzip -o /tmp/artifact.zip -d /opt/myapp",
      "chown -R ubuntu:ubuntu /opt/myapp || true",
      "chmod +x /opt/myapp/start.sh || true",
      "bash -lc 'cd /opt/myapp && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt'",

      # .env（用 printf 輸出，避免 heredoc 轉義問題）
      "bash -lc 'printf \"APP_PORT=%s\\nAPP_DB_ENGINE=mysql\\nAPP_DB_HOST=127.0.0.1\\nAPP_DB_PORT=3306\\nAPP_DB_NAME=%s\\nAPP_DB_USER=%s\\nAPP_DB_PASS=%s\\n\" ${var.app_port} ${var.db_name} ${var.db_user} ${var.db_pass} | tee /etc/myapp/.env >/dev/null'",

      # 權限給執行用戶
      "chown -R csye6225:csye6225 /opt/myapp /etc/myapp",

      # systemd unit（在單行 bash -lc 內用 heredoc，避免 HCL/YAML 解析干擾）
      "bash -lc 'cat >/etc/systemd/system/${var.service_name}.service <<\"EOF\"\n[Unit]\nDescription=FastAPI App\nAfter=network.target mysql.service\nRequires=mysql.service\n\n[Service]\nUser=csye6225\nGroup=csye6225\nEnvironmentFile=/etc/myapp/.env\nWorkingDirectory=/opt/myapp\nExecStart=/bin/bash -lc \"/opt/myapp/start.sh\"\nRestart=on-failure\nRestartSec=5\n\n[Install]\nWantedBy=multi-user.target\nEOF'",

      # 重新載入並開機自動啟動（AMI 啟用時才會真正啟動）
      "systemctl daemon-reload",
      "systemctl enable ${var.service_name}"
    ]
  }
}
