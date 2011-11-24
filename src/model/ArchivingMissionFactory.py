'''
Created on Apr 4, 2011

@author: samuel
'''

import time, re, os, shutil
from model.AbstractObject import AbstractObject
from model.ArchivingMission import ArchivingMission

class ArchivingMissionFactory(AbstractObject):
    def __init__(self, archiving_domain):
        super(ArchivingMissionFactory, self).__init__()
        self.archiving_domain = archiving_domain
        self.app = self.archiving_domain.app

    # ------------------------- MAIN METHODS -----------------------------
        
    def get_arch_mssns_ready_to_be_prepared(self, project):
        arch_mssns = []
        if project.has_start_archiving_file(): 
            self.log.info("Found start archiving file in drop-folder for project %s" % project.name)
            try:
                arch_mssn = self.new_from_drop_folder(project)
                self.move_files_to_arch_mssn_folder(project, arch_mssn)
            except:
                self.log.error("Failed to prepare files in drop-folder for project %s" % project.name)
                raise        
        else:
            self.log.info("No start archiving file for project %s" % project.name)
        
        self.log.info("Checking for existing arch_mssn folders for project %s" % project.name)
        existing_arch_mssns = self.init_existing(project, ["drop_folder"])
        project.arch_mssns = existing_arch_mssns
        existing_arch_mssns_to_be_prepared = project.get_arch_mssns_with_states(["new", "failed_prepare_for_upload"])
        arch_mssns.extend(existing_arch_mssns_to_be_prepared)
        
        return arch_mssns
    
    def get_arch_mssns_ready_for_upload(self, project): 
        self.log.info("Checking for arch_mssns ready to be uploaded, in upload cache for project %s" % project.name)
        project.arch_mssns = self.init_existing(project, folders_to_check=["upload_cache"])
        arch_mssns_ready_to_be_uploaded = project.get_arch_mssns_with_states(["prepared_for_upload", "failed_upload"])
        return arch_mssns_ready_to_be_uploaded

    def get_uploaded_arch_mssns(self, project):
        self.log.info("Checking for uploaded arch_mssns, to create confirm files for, for project %s" % project.name)
        self.init_existing(project, folders_to_check=["upload_cache", "confirm_folder"])
        arch_mssns = project.get_arch_mssns_with_states(["uploaded"])
        return arch_mssns
    
    # ----------------------- HELPER METHODS ---------------------------
    
    def new_from_drop_folder(self, project):
        '''Create the hidden working folder, with access rights only for the current user 
        (which will be root), in order to prevent interference by the user'''

        retries_left = int(self.app.config.options["createtempfolder_retries"])
        success = False
        arch_mssn = ArchivingMission(self.archiving_domain, project)

        while not success and retries_left > 0:
            try:
                arch_mssn.folder.create(0700)
                arch_mssn.lock_main_folder()
                success = True
                self.log.info("Successfully created arch_mssn folder %s" % arch_mssn.folder.path)
                arch_mssn.unlock_main_folder() # It must be unlocked, so it is not skipped in a later stage
            except Exception:
                self.log.warn("Failed to ensure_exists folder, so trying again in %ss ... (%s)" % (str(self.app.config.options["createtempfolder_waittime"]), arch_mssn.folder.path))
                time.sleep(int(self.app.config.options["createtempfolder_waittime"]))

                arch_mssn = ArchivingMission(self.archiving_domain, project)
                retries_left -= 1
                
        if retries_left == 0:
            errormsg = "Failed creating arch_mssn folder for project %s after %d retries. Giving up." % (project.name, int(self.app.config.options["createtempfolder_retries"]))
            self.log.error(errormsg)
            raise Exception(errormsg)

        return arch_mssn


    def init_existing(self, project, folders_to_check=["drop_folder", "upload_cache", "confirm_folder"]):
        def extract_arch_mssn_id(path):
            m = re.match(".*\/(\.)?(arch_mssn-.*)", path)
            arch_mssn_id = m.group(2)
            return arch_mssn_id
        
        arch_mssn_folder_paths = []
        arch_mssn_ids_added = []

        if "confirm_folder" in folders_to_check:
            new_paths = self.get_arch_mssn_folder_paths_from_folder(project.confirmation_files_folder)
            for new_path in new_paths:
                arch_mssn_id = extract_arch_mssn_id(new_path)
                if extract_arch_mssn_id(new_path) not in arch_mssn_ids_added:
                    arch_mssn_folder_paths.append(new_path)
                    arch_mssn_ids_added.append(arch_mssn_id)

        if "upload_cache" in folders_to_check:
            new_paths = self.get_arch_mssn_folder_paths_from_folder(project.uploadcache_proj_folder)
            for new_path in new_paths:
                arch_mssn_id = extract_arch_mssn_id(new_path)
                if extract_arch_mssn_id(new_path) not in arch_mssn_ids_added:
                    arch_mssn_folder_paths.append(new_path)
                    arch_mssn_ids_added.append(arch_mssn_id)

        if "drop_folder" in folders_to_check:
            new_paths = self.get_arch_mssn_folder_paths_from_folder(project.drop_folder, hidden_folders=True)
        for new_path in new_paths:
            arch_mssn_id = extract_arch_mssn_id(new_path)
            if extract_arch_mssn_id(new_path) not in arch_mssn_ids_added:
                arch_mssn_folder_paths.append(new_path)
                arch_mssn_ids_added.append(arch_mssn_id)

        arch_mssns = []
        if len(arch_mssn_folder_paths) > 0:
            for arch_mssn_path in arch_mssn_folder_paths:
                arch_mssn = self.init_new_arch_mssn_from_path(project, arch_mssn_path)
                arch_mssn.detect_state_from_file_system()
                arch_mssns.append(arch_mssn)
        else:
            self.log.warn("No existing archiving missions found for project %s" % project.name)
                
        return arch_mssns
        
    def init_new_arch_mssn_from_path(self, project, arch_mssn_path):
        id = self.extract_arch_mssn_id_from_path(arch_mssn_path)
        arch_mssn = ArchivingMission(self.archiving_domain, project, id)
        return arch_mssn
    
    def get_arch_mssn_folder_paths_from_folder(self, folder, hidden_folders=False):
        arch_mssn_folder_paths = []

        if not folder.exists():
            self.log.warn("Folder does not exist: %s" % folder.path)
        else:
            try:
                folder_content = folder.list_files()
            except OSError:
                self.log.error("Could not list directory: %s. Does it exist?" % folder)
                raise
            
            for folder_item in folder_content:
                if ((not hidden_folders and re.match(self.app.config.options["arch_mssn_id_pattern"], folder_item)) or
                    (hidden_folders and re.match("\.%s" % self.app.config.options["arch_mssn_id_pattern"], folder_item))):
                    
                    item_path = os.path.join(folder.path, folder_item)
                    if not os.path.exists(item_path):
                        self.log.warn("Folder does not exist: %s" % item_path)
                    else:
                        if not os.path.isdir(item_path):
                            self.log.warn("Item is not a folder: %s" % item_path)
                        elif os.path.isdir(item_path):
                            arch_mssn_folder_paths.append(item_path)
        
        return arch_mssn_folder_paths        

    def extract_arch_mssn_id_from_path(self, path):
        matches = re.match(".*(%s).*" % self.app.config.options["arch_mssn_id_pattern"], path)
        if matches is None:
            raise Exception("Could not extract archiving mission id from path: %s" % path)
        else: 
            arch_mssn_id = matches.group(1)
        return arch_mssn_id
    
    def move_files_to_arch_mssn_folder(self, project, arch_mssn):
        '''
        Move away files to be transferred, to an invisible folder in the current drophere-
        folder, to avoid interference from the user
        '''
        items_tomove = project.drop_folder.get_files_matching_pattern(pattern="", antipattern=".*%s.*" % self.app.config.options["arch_mssn_id_pattern"])
        
        if len(items_tomove) == 0:
            errmsg = "No files to move from main drop folder into archiving mission folder, for project %s" % project.name
            self.log.error(errmsg)
            raise Exception(errmsg)
        
        for item_to_move in items_tomove:
            item_to_move_path = os.path.join(project.drop_folder.path, item_to_move.name)
            if not re.match(".*%s.*" % self.app.config.options["arch_mssn_id_pattern"], item_to_move_path) \
                and not re.match("archiving_in_progress.lock", item_to_move_path):
                
                dest_file_path = os.path.join(arch_mssn.folder.path, item_to_move.name)
                try:
                    shutil.move(item_to_move_path, dest_file_path)
                except:
                    self.log.error("Could not move file '%s' in drop folder %s" % (item_to_move, project.drop_folder.path))
                    raise
            self.log.info("Successfully moved file '%s' to temporary working folder: %s" % (item_to_move.path, arch_mssn.folder.path))
            