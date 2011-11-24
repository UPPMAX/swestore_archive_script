'''
Created on Apr 4, 2011

@author: samuel
'''

import os, utils, re, datetime, shutil

from model.AbstractObject import AbstractObject
from model.ArchivingMissionFolder import ArchivingMissionFolder
from model.File import File
from model.Folder import Folder
from model.FileChunk import FileChunk
from model.OSUtils import OSUtils
from model.ApplicationLock import ApplicationLock

class ArchivingMission(AbstractObject):
    
    def __init__(self, archiving_domain, project, id=None):
        super(ArchivingMission, self).__init__()

        if id is None:
            self.id = self.generate_new_arch_mssn_id()
        else:
            self.id = id

        # ensure_exists the link between itself and it's domain
        self.archiving_domain = archiving_domain
        self.app = self.archiving_domain.app
        # ensure_exists the link between itself and it's project (from each end)
        self.project = project
        self.project.arch_mssns.append(self)
        
        arch_mssn_folder_name_hidden = ".%s" % self.id # Make folder name start with a dot TODO: What's this?
        arch_mssn_folder_name = self.id # Make folder name start with a dot TODO: What's this?
        
        self.folder = ArchivingMissionFolder(self, os.path.join(project.drop_folder.path, arch_mssn_folder_name_hidden))
        self.uploadcache_proj_folder = ArchivingMissionFolder(self, os.path.join(project.uploadcache_proj_folder.path, arch_mssn_folder_name))
        self.confirmation_files_folder = ArchivingMissionFolder(self, os.path.join(project.confirmation_files_folder.path, arch_mssn_folder_name))
        self.file_chunks = []
        
        self.lock = None
        self.lock_file = File(os.path.join(self.folder.path, "archiving_in_progress.lock"))
        self.lock_file_uploadcache = File(os.path.join(self.uploadcache_proj_folder.path, "archiving_in_progress.lock"))
        
        self.state = "undefined"
        self.state_file_new                          = File(os.path.join(self.folder.path, "archiving_state.new"))
        self.state_file_failed_prepare_for_upload1   = File(os.path.join(self.folder.path, "archiving_state.failed_prepare_for_upload"))
        self.state_file_failed_prepare_for_upload2   = File(os.path.join(self.uploadcache_proj_folder.path, "archiving_state.failed_prepare_for_upload"))
        self.state_file_prepared_for_upload1         = File(os.path.join(self.folder.path, "archiving_state.prepared_for_upload"))
        self.state_file_prepared_for_upload2         = File(os.path.join(self.uploadcache_proj_folder.path, "archiving_state.prepared_for_upload"))
        self.state_file_failed_upload                = File(os.path.join(self.uploadcache_proj_folder.path, "archiving_state.failed_upload"))
        self.state_file_uploaded                     = File(os.path.join(self.uploadcache_proj_folder.path, "archiving_state.uploaded"))
        self.state_file_failed_create_confirm_files  = File(os.path.join(self.uploadcache_proj_folder.path, "archiving_state.failed_create_confirm_files"))
        self.state_file_created_confirm_files        = File(os.path.join(self.uploadcache_proj_folder.path, "archiving_state.created_confirm_files"))
        
    # ------------------------- MAIN ACTIONS -----------------------------

    def prepare_for_upload(self):
        if self.state not in ["new", "failed_prepare_for_upload"]:
            self.log.info("Found existing arch_mssn %s, but had not status new or failed_prepare_for_upload" % self.id)
        else:
            self.log.info("Now preparing %s in project %s for upload ..." % (self.id, self.project.name))
            
            # Some assertions
            self.uploadcache_proj_folder.ensure_exists()
            File(self.app.config.options["tarexcludepatternsfile"]).assert_exists()
    
            self.partition_files_in_chunks()
                        
            for file_chunk in self.file_chunks:
                file_chunk.create_as_tar_file_in_upload_cache()
                file_chunk.create_meta_file()
                if self.app.config.options["create_par2_files"] == "True": # TODO: Verify correct behaviour!
                    file_chunk.create_par2_files()
                
            self.set_upload_cache_owner_to_upload_user() # Must be run as root!
            
    def upload(self):
        '''Upload all files that are ready for upload'''
        
        files_to_upload = []
        
        meta_files = self.uploadcache_proj_folder.get_files_matching_pattern(".*\.tar\.meta")
        for meta_file in meta_files:
            self.log.debug("Found meta meta_file: %s (path: %s) " % (meta_file.name, meta_file.path))
            tar_file_basename = utils.rchop(meta_file.name, ".tar.meta")
            files_to_upload.extend(self.uploadcache_proj_folder.get_files_matching_pattern("%s(\.tar\.split\d{5}|\.vol\d{3}\+\d{2}\.par2)?" % tar_file_basename))
            
        if len(files_to_upload) == 0:
            self.log.warn("No files to upload, for archiving mission %s in project %s" % (self.name, self.project.path))
        else:
            for file in files_to_upload:
                swestore_path = self.create_swestore_path(self, file)
                if not self.swestore_file_is_uploaded(swestore_path):
                    try:
                        self.upload_file(file, swestore_path)
                    except:
                        self.log.error("Failed to upload file %s" % file.path)
                        raise
                else:
                    self.log.info("File already uploaded, so skipping: %s" % swestore_path)            
                
    def create_confirm_files(self):
        confirm_folder_path = os.path.join(self.project.folder.path,  self.app.config.options["confirm_files_path_rel"], self.id)
        confirm_folder = Folder(confirm_folder_path)
        confirm_folder.ensure_exists()
        
        file_names_in_upload_cache = self.uploadcache_proj_folder.list_files()
        file_names = self.get_strings_matching_pattern_from_list(".*\.meta", file_names_in_upload_cache)
        for file_name in file_names:
            src_path = os.path.join(self.uploadcache_proj_folder.path, file_name)
            dest_path = os.path.join(confirm_folder.path, file_name)
            try:
                shutil.copy(src_path, dest_path)
                self.log.info("Successfully moved file %s to %s" % (src_path, dest_path))
            except:
                self.log.error("Could not move file %s to %s" % (src_path, dest_path))
                raise                
        
    # --------------------- HELPER METHODS -----------------------------------
    
    def partition_files_in_chunks(self):
        '''Divide the files/folders depending on their size into approximately
        equally sized chunks. If one single file/folder exceeds the maximum chunk
        size, the chunk is told to be split (which happens physically later on).'''
        
        files_and_folders = self.get_file_list_sorted_by_size()

        file_chunk = FileChunk(self)
        for file in files_and_folders:
            file_size = file.get_size()
            rem_size = file_chunk.get_remaining_size()
            if (file_size >= rem_size) and not file_chunk.is_empty():
                # Store away current file chunk, and start filling a new one
                self.file_chunks.append(file_chunk)
                file_chunk = FileChunk(self)
            file_chunk.add_file(file)
        self.file_chunks.append(file_chunk)
            
    def set_upload_cache_owner_to_upload_user(self):
        '''Change owner of the uploadcache folder for the current project to a user
        which has the required credentials for uploading the files to SweStore'''

        uid = int(self.archiving_domain.app.config.options["swestoreuploaduid"])
        gid = int(self.archiving_domain.app.config.options["swestoreuploadgid"])
        
        try:
            os.chown(self.uploadcache_proj_folder.path, uid, gid) 
        except:
            self.log.error("Failed to chown folder to user with uid %d and gid %d. Are you really running as root?" % (uid, gid))
            raise
        
    # ----------------------- UPLOAD HELPER METHODS ------------------------------

    def create_swestore_path(self, arch_mssn, file_to_upload):
        swestore_path = os.path.join(self.app.config.options["swestorebasepath"], arch_mssn.project.name, arch_mssn.id, file_to_upload.name)
        return swestore_path
    
    def swestore_file_is_uploaded(self, swestore_path):
        check_exist_cmd = ["ngls", swestore_path]
        (stdout, stderr, returncode) = OSUtils().exec_command(check_exist_cmd, exception_on_nonzero_return_code=False)
        if returncode != 0:
            if re.match(".*No such file or directory.*", stderr, re.MULTILINE|re.DOTALL):
                return False
            else:
                raise Exception("Listing of file did not succeed! Have you ran grid-proxy-init?")
        else:
            return True
            
    def upload_file(self, file, path_on_swestore):
        self.log.info("Uploading '%s' to '%s'" % (file.path, path_on_swestore))
        upload_cmd = ["ngcp", "-r", "5", "-d", str(self.app.config.options["ngcp_debug_level"]), file.path, path_on_swestore]
        retries_left = int(self.app.config.options["uploadretries"])
        while retries_left > 0: 
            try:
                OSUtils().exec_command(upload_cmd)
                self.log.info("Upload successful!")
                retries_left = 0 # Break the loop
            except:
                retries_left -= 1
                if retries_left > 0:
                    self.log.warn("Failed uploading, trying again %d times ..." % retries_left)
                else:
                    raise
            
    # ----------------- CREATE CONFIRM FILES HELPER METHODS ------------------------
        
    def get_strings_matching_pattern_from_list(self, pattern, list):
        result_list = []
        for item in list:
            if re.match(pattern, item) and item not in result_list:
                result_list.append(item)

        return result_list        

    # ------------------- SOMEWHAT GENERIC HELPER METHODS ------------------------

    def get_file_list_sorted_by_size(self):
        
        '''Get a list of files and folders sorted per size, so that it can be used 
        to partition file in suitable sized chunks for each tar archive'''
        
        files = self.folder.get_files_matching_pattern(self.app.config.options["allowedfilename_pattern"], self.app.config.options["excludedfilename_pattern"], recursive=True, only_empty_folders=True)
        
        if len(files) == 0:
            errmsg = "No files for arch mssn folder: %s" % self.folder.path
            self.log.error(errmsg)
            raise Exception(errmsg)

        files_sorted_by_size = sorted(files, key=lambda file: file.get_size())
        
        return files_sorted_by_size

    
    def get_folders_in_folder_matching_pattern(self, folder, pattern, antipattern=""):
        '''Method used as a more secure alternative to "glob". It returns all files in 
        the specified folders (except files in subfolders), whose filenames match the
        specified regex pattern'''
        
        resultfiles = []
        try:
            # List all files in the directory
            files = os.listdir(folder)
            for file in files:
                # If they match the pattern ....
                if (re.match(pattern, file) and antipattern=="") or (re.match(pattern, file) and not re.match(antipattern, file)):
                    filepath = os.path.join(folder, file)
                    # Then add them to the resulting list ...
                    resultfiles.append(filepath)
        except Exception:
            self.logger.error("Could not get files in folder %s, matching pattern %s (antipattern %s)" % (folder, pattern, antipattern))
            raise
        return resultfiles

    def get_no_of_file_chunks(self):
        return len(self.file_chunks)        
        
    
    def generate_new_arch_mssn_id(self):
        time_part = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        arch_mssn_id = "arch_mssn-%s" % time_part
        return arch_mssn_id

        
    def detect_state_from_file_system(self):
        if self.state_file_failed_create_confirm_files.exists():
            self.set_state_failed_create_confirm_files()
        elif self.state_file_created_confirm_files.exists():
            self.set_state_created_confirm_files()
        elif self.state_file_failed_upload.exists():
            self.set_state_failed_upload()
        elif self.state_file_uploaded.exists():
            self.set_state_uploaded()
        elif self.archiving_domain.app.action in ["prepare"] and self.state_file_failed_prepare_for_upload1.exists():
            self.set_state_failed_prepare_for_upload()
        elif self.state_file_failed_prepare_for_upload2.exists():
            self.set_state_failed_prepare_for_upload()
        elif self.archiving_domain.app.action in ["prepare"] and self.state_file_prepared_for_upload1.exists():
            self.log.info("State file exists: %s" % self.state_file_prepared_for_upload1.path)
            self.set_state_prepared_for_upload()
        elif self.state_file_prepared_for_upload2.exists():
            self.log.info("State file exists: %s" % self.state_file_prepared_for_upload2.path)
            self.set_state_prepared_for_upload()
        elif self.state_file_new.exists():
            self.set_state_new()

    def set_state_new(self):
        self.state = "new"
        self.log.debug("Set state of archiving mission %s to: %s" % (self.id, self.state))
        self.ensure_delete_all_state_files()
        self.state_file_new.ensure_exists()

    def set_state_prepared_for_upload(self):
        self.state = "prepared_for_upload"
        self.log.debug("Set state of archiving mission %s to: %s" % (self.id, self.state))
        self.ensure_delete_all_state_files()
        
        # We can't be sure that the original drophere folder does exist, so we better
        # check that first
        if self.archiving_domain.app.action in ["prepare"]:
            if self.folder.exists():
                self.state_file_prepared_for_upload1.ensure_exists()
            else:
                self.log.warn("Archiving mission folder missing in project's drophere folder: %s" % self.folder.path)

        if self.uploadcache_proj_folder.exists():
            self.state_file_prepared_for_upload2.ensure_exists()
        else:
            self.log.warn("Archiving mission folder missing in project's upload cache folder: %s" % self.uploadcache_proj_folder.path)
        
    def set_state_failed_prepare_for_upload(self):
        self.state = "failed_prepare_for_upload"
        self.log.debug("Set state of archiving mission %s to: %s" % (self.id, self.state))
        self.ensure_delete_all_state_files()

        # We can't be sure that the original drophere folder does exist, so we better
        # check that first
        if self.archiving_domain.app.action in ["prepare"]:
            if self.folder.exists():
                self.state_file_failed_prepare_for_upload1.ensure_exists()
            else:
                self.log.warn("Archiving mission folder missing in project's drophere folder: %s" % self.folder.path)

        if self.uploadcache_proj_folder.exists():
            self.state_file_failed_prepare_for_upload2.ensure_exists()
        else:
            self.log.warn("Archiving mission folder missing in project's upload cache folder: %s" % self.uploadcache_proj_folder.path)

    def set_state_uploaded(self):
        self.state = "uploaded"
        self.log.debug("Set state of archiving mission %s to: %s" % (self.id, self.state))
        self.ensure_delete_all_state_files()
        self.state_file_uploaded.ensure_exists()

    def set_state_failed_upload(self):
        self.state = "failed_upload"
        self.log.debug("Set state of archiving mission %s to: %s" % (self.id, self.state))
        self.ensure_delete_all_state_files()
        self.state_file_failed_upload.ensure_exists()

    def set_state_created_confirm_files(self):
        self.state = "created_confirm_files"
        self.log.debug("Set state of archiving mission %s to: %s" % (self.id, self.state))
        self.ensure_delete_all_state_files()
        self.state_file_created_confirm_files.ensure_exists()

    def set_state_failed_create_confirm_files(self):
        self.state = "failed_create_confirm_files"
        self.log.debug("Set state of archiving mission %s to: %s" % (self.id, self.state))
        self.ensure_delete_all_state_files()
        self.state_file_failed_create_confirm_files.ensure_exists()
        
    def ensure_delete_all_state_files(self):
        action = self.archiving_domain.app.action
        if action in ["prepare", "createconfirmfiles"]:
            self.state_file_new.ensure_delete()
            self.state_file_failed_prepare_for_upload1.ensure_delete()
            self.state_file_failed_prepare_for_upload2.ensure_delete()
            self.state_file_prepared_for_upload1.ensure_delete()
            self.state_file_prepared_for_upload2.ensure_delete()
            self.state_file_failed_upload.ensure_delete()
            self.state_file_uploaded.ensure_delete()
            self.state_file_failed_create_confirm_files.ensure_delete()
            self.state_file_created_confirm_files.ensure_delete()
        elif action == "upload":
            self.state_file_prepared_for_upload2.ensure_delete()
            self.state_file_failed_upload.ensure_delete()
            self.state_file_uploaded.ensure_delete()
        
    def lock_main_folder(self):
        '''Get an archiving_domain lock for the main folder (located under the project's drop folder)'''
        self.lock_file.ensure_exists()
        self.lock = ApplicationLock(self.lock_file)
        
    # ------------------- LOCK FILE METHODS ------------------------------
        
    def unlock_main_folder(self):
        if self.lock is not None:
            self.lock.unlock()
        if self.lock_file.exists():
            self.lock_file.delete()
            
    def lock_uploadcache_folder(self):
        '''Get an archiving_domain lock for the main folder (located under the project's drop folder)'''
        self.log.debug("Trying to lock upload cache folder for %s in project %s ..." % (self.id, self.project.name))
        self.lock_file_uploadcache.ensure_exists()
        self.lock_uploadcache = ApplicationLock(self.lock_file_uploadcache)
        self.log.debug("Succeded to lock upload cache folder for %s in project %s ..." % (self.id, self.project.name))
        
    def unlock_uploadcache_folder(self):
        if self.lock_uploadcache is not None:
            self.lock_uploadcache.unlock()   
        if self.lock_file_uploadcache.exists():
            self.lock_file_uploadcache.delete()
            
    def has_unlocked_main_folder(self):
        return self.folder.exists() and not self.lock_file.exists()

    def has_unlocked_uploadcache_folder(self):
        return self.uploadcache_proj_folder.exists() and not self.lock_file_uploadcache.exists()
    