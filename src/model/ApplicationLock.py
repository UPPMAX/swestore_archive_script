'''
Created on Apr 4, 2011

@author: samuel
'''
import os, fcntl, errno
from model.AbstractObject import AbstractObject

class ApplicationLock(AbstractObject):
## "Stolen" from http://code.activestate.com/recipes/576891/
    '''
    Ensures application is running only once, by using a lock file.

    Ensure call to lock works.  Then call unlock at program exit.

    You cannot read or write to the lock file, but for some reason you can
    remove it.  Once removed, it is still in a locked state somehow.  Another
    application attempting to lock against the file will fail, even though
    the directory listing does not show the file.  Mysterious, but we are glad
    the lock integrity is upheld in such a case.

    Instance variables:
        lockfile  -- Full path to lock file
        lockfd    -- File descriptor of lock file exclusively locked
    '''
    def __init__ (self, lockfile):
        self.lockfile = lockfile
        self.lockfd = None

    def lock (self):
        '''
        Creates and holds on to the lock file with exclusive access.
        Returns True if lock successful, False if it is not, and raises
        an exception upon operating system errors encountered creating the
        lock file.
        '''
        try:
            #
            # Create or else open and trucate lock file, in read-write mode.
            #
            # A crashed app might not ensure_delete the lock file, so the
            # os.O_CREAT | os.O_EXCL combination that guarantees
            # atomic ensure_exists isn't useful here.  That is, we don't want to
            # fail locking just because the file exists.
            #
            # Could use os.O_EXLOCK, but that doesn't exist yet in my Python
            #
            self.lockfd = os.open (self.lockfile.path,
                                   os.O_TRUNC | os.O_CREAT | os.O_RDWR)

            # Acquire exclusive lock on the file, but don't block waiting for it
            fcntl.flock (self.lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)

            # Writing to file is pointless, nobody can see it
            os.write (self.lockfd, "My Lockfile")

            return True
        except (OSError, IOError), e:
            # Lock cannot be acquired is okay, everything else reraise exception
            if e.errno in (errno.EACCES, errno.EAGAIN):
                return False
            else:
                raise

    def unlock (self):
        try:
            # FIRST unlink file, then close it.  This way, we avoid file
            # existence in an unlocked state
            os.unlink (self.lockfile.path)
            # Just in case, let's not leak file descriptors
            if self.lockfd is not None:
                os.close (self.lockfd)
        except (OSError, IOError), e:
            # Ignore error destroying lock file.  See class doc about how
            # lockfile can be erased and everything still works normally.
            pass        