'''
Created on Apr 4, 2011

@author: samuel
'''

import logging
from model.AbstractObject import AbstractObject 
from model.ArchivingDomain import ArchivingDomain 
from model.ConfigHandler import ConfigHandler

class Application(AbstractObject):
    def __init__(self, configfile_path):
        super(Application, self).__init__()
        self.projects = []
        self.action = ""
        self.config = ConfigHandler()
        self.config.init_from_file(configfile_path)
        self.init_logger()
        
    def init_action(self, action):
        self.action = action
        # Initializing Services
        self.archiving_domain = ArchivingDomain(self)

    def run(self):
        action = self.action 
        
        if action == 'prepare':
            self.archiving_domain.prepare_for_upload()

        elif action == 'upload':
            self.archiving_domain.upload()
            
        elif action == 'createconfirmfiles':
            self.archiving_domain.create_confirm_files()
        
        
    def init_logger(self):
        self.log.setLevel(int(self.config.options["logging_level"]))
        streamHandler = logging.StreamHandler()
        # Init the custom log format
        #formatter = logging.Formatter("%(levelname)s %(asctime)s %(funcName)s %(lineno)d %(message)s")
        formatter = logging.Formatter("%(levelname)s %(asctime)s %(message)s")
        streamHandler.setFormatter(formatter)
        self.log.addHandler(streamHandler)
        
        