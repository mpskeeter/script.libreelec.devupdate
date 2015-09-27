from __future__ import division

import os
import glob
import functools
import stat

import xbmc, xbmcaddon, xbmcgui

import openelec
import log
import addon
import constants


ok = xbmcgui.Dialog().ok
yesno = xbmcgui.Dialog().yesno
notification = xbmcgui.Dialog().notification

def connection_error(msg):
    ok("Connection Error", msg,
       "Please check you have a connection to the internet.")

    
def bad_url(url, msg="URL not found."):
    ok("URL Error", msg, url, "Please check the URL.")

    
def url_error(url, msg):
    log.log_exception()
    ok("URL Error", msg, url, "Please check the log file.")

    
def write_error(path, msg):
    log.log_exception()
    ok("Write Error", msg, path,
       "Check the download directory in the addon settings.")
    addon.open_settings()

    
def decompress_error(path, msg):
    log.log_exception()
    ok("Decompression Error",
       "An error occurred during decompression:",
       " ", msg)


@log.with_logging("Removed file", "Could not remove file")
def remove_file(file_path):
    log.log("Removing {}".format(file_path))
    try:
        os.remove(file_path)
    except OSError:
        return False
    else:
        return True


@log.with_logging("Created directory {}", log_exc=False)
def create_directory(path):
    os.mkdir(path)


def remove_update_files():
    tar_update_files = glob.glob(os.path.join(openelec.UPDATE_DIR, '*tar'))
    success = all(remove_file(tar) for tar in tar_update_files)

    if success:
        addon.set_setting('update_pending', 'false')
    return success


def get_arch():
    if addon.get_setting('set_arch') == 'true':
        return addon.get_setting('arch')
    else:
        return openelec.ARCH


def notify(msg, time=12000):
    notification(addon.name, msg, addon.icon_path, time)

    
def busy():
    xbmc.executebuiltin("ActivateWindow(busydialog)")


def not_busy():
    xbmc.executebuiltin("Dialog.Close(busydialog)")

    
def showbusy(f):
    @functools.wraps(f)
    def busy_wrapper(*args, **kwargs):
        busy()
        try:
            return f(*args, **kwargs)
        finally:
            not_busy()
    return busy_wrapper


def build_check_prompt():
    check_prompt = int(addon.get_setting('check_prompt'))
    return check_prompt == 2 or (check_prompt == 1 and not xbmc.Player().isPlayingVideo())


def ensure_trailing_slash(path):
    return path if path.endswith('/') else path + '/'


@log.with_logging(msg_error="Unable to check if another instance is running")
def is_running():
    running = xbmcgui.Window(10000).getProperty('DevUpdateRunning') == 'True'
    log.log("Another instance is running" if running else "No other instance is running")
    return running


@log.with_logging("Set running flag", "Unable to set running flag")
def set_running():
    xbmcgui.Window(10000).setProperty('DevUpdateRunning', 'True')


@log.with_logging("Cleared running flag", "Unable to clear running flag")
def set_not_running():
    xbmcgui.Window(10000).clearProperty('DevUpdateRunning')


@log.with_logging(msg_error="Unable to make script executable")
def make_script_executable(script_path):
    os.chmod(script_path, stat.S_IXUSR|stat.S_IRUSR|stat.S_IWUSR)


@log.with_logging(msg_error="Unable to create script symbolic link", log_exc=False)
def create_script_symlink(script_path, symlink_path):
    os.symlink(script_path, symlink_path)


def install_cmdline_script():
    """ Creates a symbolic link to the command line download script
    in the root user home directory. The script can then be invoked
    by running:

        ./devupdate
    """

    SCRIPT_NAME = "download.py"
    script_path = os.path.join(addon.src_path, SCRIPT_NAME)

    SYMLINK_NAME = "devupdate"
    symlink_path = os.path.join(os.path.expanduser('~'), SYMLINK_NAME)

    make_script_executable(script_path)

    create_script_symlink(script_path, symlink_path)


def maybe_schedule_extlinux_update():
    if (not openelec.ARCH.startswith('RPi') and
        addon.get_setting('update_extlinux') == 'true'):
        open(os.path.join(addon.data_path, constants.UPDATE_EXTLINUX_FILE), 'w').close()


def maybe_run_backup():
    backup = int(addon.get_setting('backup'))
    if backup == 0:
        do_backup = False
    elif backup == 1:
        do_backup = yesno("Backup", "Run Backup now?", "This is recommended")
        log.log("Backup requested")
    elif backup == 2:
        do_backup = True
        log.log("Backup always")

    if do_backup:
        xbmc.executebuiltin('RunScript(script.xbmcbackup, mode=backup)', True)
        xbmc.sleep(10000)
        window = xbmcgui.Window(10000)
        while (window.getProperty('script.xbmcbackup.running') == 'true'):
            xbmc.sleep(5000)
