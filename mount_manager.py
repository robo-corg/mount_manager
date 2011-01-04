import yaml
import subprocess
import os
from time import sleep
from threading import Timer
from threading import Event

class MountManager:
    mounts_dir = os.path.join(os.environ['HOME'],'.mounts/')
    
    def __init__(self):
        self.mount_types = dict()
        self.mounts = []
        self.check_timer = None
        self.stopping = Event()

    def load_mount_file(self,mount_file_name):
        mount_file = open(mount_file_name)
        mount_conf = yaml.load(mount_file)
        mount_file.close()

        if not 'type' in mount_conf:
            raise 'type required for mount config.'
            
        mount_type = mount_conf['type']

        if not mount_type in self.mount_types:
            raise 'Type %s not a valid mount type.' % (mount_type)

        return self.mount_types[mount_type](mount_conf)

    def load_config(self):
        mounts_files = [os.path.join(self.mounts_dir,path) for path in os.listdir(self.mounts_dir)]
        
        mounts_files = [path for path in mounts_files if os.path.isfile(path)]
        self.mounts += map(self.load_mount_file, mounts_files)

    def wait_for_mounts(self):
        while True:
            try:
                os.wait()
            except OSError:
                sleep(30)

    def do_check(self):
        for mount in self.mounts:
            if self.stopping.is_set():
                return
            
            print 'Checking mount: %s' % (str(mount))
            if not mount.check():
                print 'Restarting mount: %s' % (str(mount))
                mount.restart()

    def check_timer_loop(self):
        try:
            self.do_check()
        finally:    
            if self.stopping.is_set():
                return

            self.check_timer = Timer(30, self.do_check)
            self.check_timer.start()

    def start_checks(self):
        self.do_check()

    def start(self):
        self.stopping.clear()
        
        try:
            for mount in self.mounts:
                mount.start()

            sleep(10)

            self.start_checks()

            self.wait_for_mounts()

           # self.stopping.wait()

        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        self.stopping.set()
        
        if self.check_timer != None:
            self.check_timer.cancel()
            self.check_timer = None
            
        for mount in self.mounts:
            mount.stop()
    

class Mount:
    def __init__(self,mount_point):
        self.mount_point = mount_point

    def start(self):
        pass

    def stop(self):
        pass

    def restart(self):
        self.stop()
        self.start()

    def is_running(self):
        return True

    def check(self):
        if not self.is_running():
            return False

        return True

    def __str__(self):
        return self.mount_point

class SSHFSMount(Mount):
    def __init__(self, server, path, mount):
        Mount.__init__(self,mount)

        self.server = server
        self.path = path
        self.proc = None

    @staticmethod
    def from_conf(conf):
        kargs = conf.copy()
        del kargs['type']
        return SSHFSMount(**kargs)

    def start(self):
        umounter = subprocess.Popen(['/sbin/umount', self.mount_point])

        try:
            umounter.wait()
        except OSError:
            pass
        
        self.proc = subprocess.Popen(['/Users/amcharg/.local/bin/sshfs', '-f', self.server + ':' + self.path, self.mount_point, '-oauto_cache,reconnect'])
        print 'Starting sshfs with pid: %d' % self.proc.pid

    def stop(self):
        if not self.is_running():
            return
        
        if self.proc != None:            
            print 'Killing sshfs with pid: %d' % self.proc.pid
            self.proc.terminate()
            sleep(5)
            self.proc.kill()
            
            self.proc = None

    def is_running(self):
        if self.proc == None:
            return True
        
        try:
            os.kill(self.proc.pid,0)
        except OSError:
            return False
        
        return True                           

if __name__ == "__main__":
    manager = MountManager()

    manager.mount_types['sshfs'] = SSHFSMount.from_conf
    
    manager.load_config()
    manager.start()

