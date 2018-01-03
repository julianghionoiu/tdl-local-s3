import os
import signal
import socket
import subprocess
import sys
import time
import urllib2
import platform

SCRIPT_FOLDER = os.path.dirname(os.path.realpath(__file__))
CACHE_FOLDER = os.path.join(SCRIPT_FOLDER, ".cache")
STORAGE_FOLDER = os.path.join(SCRIPT_FOLDER, ".storage")


def run(command):
    if not os.path.exists(CACHE_FOLDER):
        os.mkdir(CACHE_FOLDER)
    if not os.path.exists(STORAGE_FOLDER):
        os.mkdir(STORAGE_FOLDER)

    port = 9000
    if "Windows" in platform.system():
        url = "https://dl.minio.io/server/minio/release/windows-amd64/minio.exe"
        is_shell = True
    elif "Darwin" in platform.system():
        url = "https://dl.minio.io/server/minio/release/darwin-amd64/minio"
        is_shell = False
    else:
        url = "https://dl.minio.io/server/minio/release/linux-amd64/minio"
        is_shell = False

    minio_bin = os.path.join(CACHE_FOLDER, url.split('/')[-1])
    pid_file = os.path.join(CACHE_FOLDER, "pid-" + str(port))

    if not os.path.isfile(minio_bin):
        download_and_show_progress(url, minio_bin)

    os.chmod(minio_bin, 0x755)
    if command == "start":
        my_env = {'MINIO_ACCESS_KEY': "minio_access_key",
                  'MINIO_SECRET_KEY': "minio_secret_key",
                  'MINIO_BROWSER': "off"}
        execute(my_env, [minio_bin, "server", STORAGE_FOLDER], is_shell, pid_file)
        wait_until_port_is_open(port, 5)
    elif command == "stop":
        kill_process(pid_file)


def execute(my_env, command, is_shell, pid_file):
    env_copy = os.environ.copy()
    env_copy.update(my_env)
    print "Execute: " + " ".join(command)
    proc = subprocess.Popen(command, env=env_copy, shell=is_shell)
    f = open(pid_file, "w")
    f.write(str(proc.pid))
    f.close()
    return proc


def download_and_show_progress(url, file_name):
    u = urllib2.urlopen(url)
    f = open(file_name, 'wb')
    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    print "Downloading: %s Bytes: %s" % (file_name, file_size)

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
        print status,

    f.close()


def wait_until_port_is_open(port, delay):
    n = 0
    while n < 5:
        print "Is application listening on port " + str(port) + "? "
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        if result == 0:
            print "Yes"
            return
        print "No. Retrying in " + str(delay) + " seconds"
        n = n + 1
        time.sleep(delay)


def kill_process(pid_file):
    f = open(pid_file, "r")
    try:
        pid_str = f.read()
        print "Kill process with pid: " + pid_str
        os.kill(int(pid_str), signal.SIGTERM)
    except Exception:
        f.close()
        os.remove(pid_file)


if __name__ == "__main__":
    run(sys.argv[1])
