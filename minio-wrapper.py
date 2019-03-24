import os
import platform
import signal
import socket
import subprocess
import sys
import time
import urllib.request, urllib.error, urllib.parse
import yaml

SCRIPT_FOLDER = os.path.dirname(os.path.realpath(__file__))
CACHE_FOLDER = os.path.join(SCRIPT_FOLDER, ".cache")
STORAGE_FOLDER = os.path.join(SCRIPT_FOLDER, ".storage")


def run(command, buckets_to_configure):
    if not os.path.exists(CACHE_FOLDER):
        os.mkdir(CACHE_FOLDER)
    if not os.path.exists(STORAGE_FOLDER):
        os.mkdir(STORAGE_FOLDER)

    port = 9000
    minio_server_base_url = "https://dl.minio.io/server/minio/release"
    minio_client_base_url = "https://dl.minio.io/client/mc/release"
    if "Windows" in platform.system():
        minio_server_base_url = "%s/windows-amd64/minio.exe" % minio_server_base_url
        minio_client_url = "%s/windows-amd64/mc.exe" % minio_client_base_url
        is_shell = True
    elif "Darwin" in platform.system():
        minio_server_base_url = "%s/darwin-amd64/minio" % minio_server_base_url
        minio_client_url = "%s/darwin-amd64/mc" % minio_client_base_url
        is_shell = False
    else:
        minio_server_base_url = "%s/linux-amd64/minio" % minio_server_base_url
        minio_client_url = "%s/linux-amd64/mc" % minio_client_base_url
        is_shell = False

    minio_server_bin = os.path.join(CACHE_FOLDER, minio_server_base_url.split('/')[-1])
    minio_client_bin = os.path.join(CACHE_FOLDER, minio_client_url.split('/')[-1])
    pid_file = os.path.join(CACHE_FOLDER, "pid-" + str(port))

    if not os.path.isfile(minio_server_bin):
        download_and_show_progress(minio_server_base_url, minio_server_bin)
        os.chmod(minio_server_bin, 0x755)

    if not os.path.isfile(minio_client_bin):
        download_and_show_progress(minio_client_url, minio_client_bin)
        os.chmod(minio_client_bin, 0x755)

    if command == "start":
        # Start minio server
        access_key = "local_test_access_key"
        secret_key = "local_test_secret_key"
        my_env = {'MINIO_ACCESS_KEY': access_key,
                  'MINIO_SECRET_KEY': secret_key,
                  'MINIO_BROWSER': "off"}
        execute(my_env, [minio_server_bin, "server", STORAGE_FOLDER], is_shell, pid_file)
        wait_until_port_is_open(port, 5)

        # Connect minio client to server
        execute({}, [minio_client_bin, "config", "host", "add", "s3", "http://localhost:" + str(port),
                     access_key, secret_key], is_shell)

        # Configure all the needed buckets
        for bucket in buckets_to_configure:
            bucket_path = "s3/" + bucket
            execute({}, [minio_client_bin, "mb", bucket_path], is_shell)
            execute({}, [minio_client_bin, "policy", "--recursive", "public", bucket_path], is_shell)
    elif command == "stop":
        kill_process(pid_file)


def execute(my_env, command, is_shell, pid_file=None):
    env_copy = os.environ.copy()
    env_copy.update(my_env)
    print("Execute: " + " ".join(command))
    proc = subprocess.Popen(command, env=env_copy, shell=is_shell)

    if pid_file:
        f = open(pid_file, "w")
        f.write(str(proc.pid))
        f.close()
    return proc


def download_and_show_progress(url, file_name):
    print("Downloading from: %s" % url)
    u = urllib.request.urlopen(url)
    f = open(file_name, 'wb')
    meta = u.info()
    file_size = int(meta.get_all("Content-Length")[0])
    print("Downloading: %s Bytes: %s" % (file_name, file_size))

    file_size_dl = 0
    block_sz = 8192
    while True:
        buffer = u.read(block_sz)
        if not buffer:
            break

        file_size_dl += len(buffer)
        f.write(buffer)
        status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
        status = status + chr(8) * (len(status) + 1)
        print(status, end=' ')

    f.close()


def wait_until_port_is_open(port, delay):
    n = 0
    while n < 5:
        print("Is application listening on port " + str(port) + "? ")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        if result == 0:
            print("Yes")
            return
        print("No. Retrying in " + str(delay) + " seconds")
        n = n + 1
        time.sleep(delay)


def kill_process(pid_file):
    f = open(pid_file, "r")
    try:
        pid_str = f.read()
        print("Kill process with pid: " + pid_str)
        os.kill(int(pid_str), signal.SIGTERM)
    except Exception:
        f.close()
        os.remove(pid_file)


# ~~~ Logging

def log_debug(message):
    log("[DEBUG] " + message)


def log_error(message):
    log("[ERROR] " + message)


def log_info(message):
    log("[INFO] " + message)


def log(message):
    print(time.asctime(), message)


# ~~~ Configure

LOCAL_CONFIG_ARN_MARKER = "arn:local:s3:::"


def extract_buckets_from_config_file(task_env_file):
    bucket_list = []

    log_info("Reading ECS Task Env file: " + task_env_file)
    with open(task_env_file, 'r') as stream:
        task_env_as_dict = yaml.load(stream)

    log_info("Bucket related ENV variables: ")
    for key, value in list(task_env_as_dict.items()):
        if LOCAL_CONFIG_ARN_MARKER in value:
            log_info(key + "=" + value)
            bucket_name = value.replace(LOCAL_CONFIG_ARN_MARKER, "")
            bucket_list.append(bucket_name)

    log_info("Bucket to configure: ")
    for bucket in bucket_list:
        log_info(" - " + bucket)

    return bucket_list


if __name__ == "__main__":
    command = sys.argv[1]

    buckets_to_configure = []
    if len(sys.argv) > 2:
        buckets_to_configure = extract_buckets_from_config_file(sys.argv[2])

    run(command, buckets_to_configure)
