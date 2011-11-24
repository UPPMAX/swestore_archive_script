'''
Created on Mar 4, 2011

@author: Samuel Lampa <samuel.lampa at scilifelab.uu.se>
'''
from model.AbstractDomain import AbstractDomain 
from model.ClusterProjectFactory import ClusterProjectFactory
from model.ArchivingMissionFactory import ArchivingMissionFactory

# \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
#  ArchivingDomain Class
# \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

class ArchivingDomain(AbstractDomain):
    
    '''Domain object for taking care of everything related to the actual
       archiving operation, in its different steps.'''
    
    def __init__(self, application):
        super(AbstractDomain, self).__init__()
        self.app = application
        self.arch_mssns = []

        self.project_factory = ClusterProjectFactory(self, application)
        self.arch_mssn_factory = ArchivingMissionFactory(self)

    def prepare_for_upload(self):

        projects = self.project_factory.get_projects()
        for project in projects:
            arch_mssns = self.arch_mssn_factory.get_arch_mssns_ready_to_be_prepared(project)
            for arch_mssn in arch_mssns:
                if not arch_mssn.has_unlocked_main_folder():
                    self.log.warn("Main folder locked, so skipping %s for project %s" % (arch_mssn.id, project.name))
                else:
                    self.log.info("Found archiving mission %s ready to be prepared, for project: %s" % (arch_mssn.id , project.name)) 
                    try:
                        arch_mssn.lock_main_folder()
                        arch_mssn.prepare_for_upload()
                        arch_mssn.set_state_prepared_for_upload()
                        arch_mssn.unlock_main_folder()
                    except:
                        self.log.error("Failed to prepare for upload: %s, in project %s" % (arch_mssn.id, project.name))
                        arch_mssn.set_state_failed_prepare_for_upload()
                        arch_mssn.unlock_main_folder()
                        raise #TODO: REMOVE
            

    def upload(self):
        '''Execute upload operation for all archiving missions for a project'''
        
        projects = self.project_factory.get_projects()  

        for project in projects:
            arch_mssns_to_upload = self.arch_mssn_factory.get_arch_mssns_ready_for_upload(project)
            
            for arch_mssn in arch_mssns_to_upload:
                if not arch_mssn.has_unlocked_uploadcache_folder():
                    self.log.warn("Uploadcache folder locked, so skipping upload for %s for project %s" % (arch_mssn.id, project.name))
                else:
                    self.log.info("Found archiving mission %s ready for upload, for project: %s" % (arch_mssn.id , project.name)) 
                    try:
                        arch_mssn.lock_uploadcache_folder()
                        arch_mssn.upload()
                        arch_mssn.set_state_uploaded()
                        arch_mssn.unlock_uploadcache_folder()
                    except:
                        self.log.error("Uploading failed for archiving mission %s, in project %s" % (arch_mssn.id, project.name))
                        arch_mssn.set_state_failed_upload()
                        arch_mssn.unlock_uploadcache_folder()
                    
        
    def create_confirm_files(self):
        
        projects = self.project_factory.get_projects()  
        
        for project in projects:
            arch_mssns = self.arch_mssn_factory.get_uploaded_arch_mssns(project)
            project.arch_mssns = arch_mssns
            arch_mssns_to_create_confirm_files_for = project.get_arch_mssns_with_states(["uploaded"]) #TODO: Fix!

            for arch_mssn in arch_mssns_to_create_confirm_files_for:
                if not arch_mssn.has_unlocked_uploadcache_folder():
                    self.log.warn("Uploadcache folder locked, so skipping createconfirmfiles for %s for project %s" % (arch_mssn.id, project.name))
                else:
                    try:
                        arch_mssn.lock_uploadcache_folder()
                        arch_mssn.create_confirm_files()
                        arch_mssn.set_state_created_confirm_files()
                        self.log.info("Successfully created confirm files for %s in project %s" % (arch_mssn.id, arch_mssn.project.name))
                        arch_mssn.unlock_uploadcache_folder()
                    except:
                        arch_mssn.set_state_failed_create_confirm_files()
                        self.log.error("Could not create confirm files for %s in project %s" % (arch_mssn.id, arch_mssn.project.name))
                        arch_mssn.unlock_uploadcache_folder()

