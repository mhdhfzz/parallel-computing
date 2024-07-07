import os
import json
import paramiko
import logging


def read_hosts(file_path):
    with open(file_path, "r") as file:
        data = json.load(file)
    logging.info(f"Hosts loaded: {data['hosts']}")
    return data["hosts"]


def ssh_connect(host):
    logging.info(
        f"Connecting to {host['ip']} ({
                 host['username']}@{host['host']})"
    )
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host["ip"], username=host["username"], password=host["password"])
    logging.info(
        f"Connected to {host['ip']} ({
                 host['username']}@{host['host']})"
    )
    return client


def send_file(client, local_path, remote_path):
    sftp = client.open_sftp()
    sftp.put(local_path, remote_path)
    sftp.close()
    logging.info(f"Sent file {local_path} to {remote_path}")


def check_file_exists(client, remote_path):
    if client.get_transport().remote_version.startswith("OpenSSH"):
        command = f"test -f {remote_path} && echo 'exists'"
    else:
        command = f"if exist {
            remote_path} (echo exists) else (echo doesnotexist)"

    stdin, stdout, stderr = client.exec_command(command)
    result = stdout.read().decode().strip()
    return result == "exists"


def get_remote_temp_directory(client):
    stdin, stdout, stderr = client.exec_command("uname")
    os_type = stdout.read().decode().strip().lower()

    if "linux" in os_type:
        return "/tmp"
    else:
        stdin, stdout, stderr = client.exec_command("echo %TEMP%")
        temp_path = stdout.read().decode().strip()
        return temp_path


def remote_monte_carlo_pi(client, num_samples, num_threads):
    remote_temp_dir = get_remote_temp_directory(client)
    remote_script_path = os.path.join(remote_temp_dir, "monte_carlo.py").replace(
        "\\", "/"
    )
    local_script_path = "monte_carlo.py"
    remote_utils_path = os.path.join(remote_temp_dir, "utils.py").replace("\\", "/")
    local_utils_path = "utils.py"

    if not os.path.exists(local_script_path):
        raise FileNotFoundError(
            f"{local_script_path} does not exist on the local machine"
        )

    if not os.path.exists(local_utils_path):
        raise FileNotFoundError(
            f"{local_utils_path} does not exist on the local machine"
        )

    if not check_file_exists(client, remote_script_path):
        logging.info(
            f"{remote_script_path} does not exist on remote host, sending file..."
        )
        send_file(client, local_script_path, remote_script_path)

    if not check_file_exists(client, remote_utils_path):
        logging.info(
            f"{remote_utils_path} does not exist on remote host, sending file..."
        )
        send_file(client, local_utils_path, remote_utils_path)

    python_code = f"""import sys; sys.path.append('{remote_temp_dir.replace(
        "\\", "/")}'); from monte_carlo import monte_carlo_pi_multi; result = monte_carlo_pi_multi({num_samples}, {num_threads}); print(result)"""

    stdin, stdout, stderr = client.exec_command("where python")
    python_command = stdout.readline().strip()
    if not python_command:
        stdin, stdout, stderr = client.exec_command(
            "command -v python || command -v python3"
        )
        python_command = stdout.read().decode().strip()

    command = f'{python_command} -c "{python_code}"'
    stdin, stdout, stderr = client.exec_command(command)
    result = stdout.read().decode().strip()
    error = stderr.read().decode().strip()

    if error:
        logging.error(f"Error: {error}")

    return result
