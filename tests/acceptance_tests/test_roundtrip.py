'''Test if data integrity is maintained through the whole process 
of packaging, uploading, and then downloading and unpacking again. 
Testing is done by counting number of files, and comparing md5 checksums.'''

import os, shutil, string, subprocess, re
from model.Application import Application

class testRoundTrip():
    def __init__(self):
        self.test_data_folder_structure = "/home/samuel/wksp/swestore/ArchiveOnSwestoreNG/tests/testdata/for_drophere_folder"

        self.test_proj_name = "b2222222"

        self.proj_folder = "/home/samuel/bubofake_auto/proj"
        self.drop_folder = os.path.join(self.proj_folder, self.test_proj_name, "swestore/drophere2archive")

        self.uploadcache_folder = "/home/samuel/bubofake_auto/uploadcache"
        self.uploadcache_proj_folder  = os.path.join(self.uploadcache_folder, self.test_proj_name)

        self.confirm_folder  = os.path.join(self.proj_folder, self.test_proj_name, "swestore/moved2swestore")
        self.verification_folder  = "/home/samuel/bubofake_auto/verify/"
        self.verification_proj_folder = self.verification_folder + self.test_proj_name

        self.uploadcache_proj_folder = os.path.join(self.uploadcache_folder, self.test_proj_name)
        
        self.app = Application(configfile_path="/home/samuel/wksp/swestore/ArchiveOnSwestoreNG/src/settings.autotest.cfg")
    
    # ---- Main test function ----------------------------------------------------

    def test_roundtrip(self):
        # Execution
        self.prepare_for_upload()
        
        print("Done preparing!")
        
        self.upload()
        self.create_confirm_files()
        self.download()
        self.unpack()

        self.verify_file_count()
        self.verify_adler32_sums()
        
    # ---- Verification functions ----------------------------------------------------

    def verify_file_count(self):
        assert self.folder_content_count(self.unpacked_folder1) == 7
        assert self.folder_content_count(self.unpacked_folder2) == 12
    
    def verify_adler32_sums(self):
        for unpacked_folder in self.unpacked_folders:
            for filename in os.listdir(unpacked_folder):
                file_path = os.path.join(unpacked_folder, filename)
                adler32sum_cmd = ["jacksum", "-a", "adler32", "-F", "#CHECKSUM", file_path]
                adler32sum_output = self.exec_command(adler32sum_cmd)
                adler32sum = adler32sum_output.split(" ")[0]
                print("Testing if filename %s equals its adler32sum %s ..." % (filename, adler32sum))
                assert filename == adler32sum

    # ---- Execution functions ----------------------------------------------------

    def prepare_for_upload(self):
        self.app.init_action("prepare")
        self.app.run()
    
    def upload(self):
        self.app.init_action("upload")
        self.app.run()

    def create_confirm_files(self):
        self.app.init_action("createconfirmfiles")
        self.app.run()
    
    def download(self):
        download_cmd = ["ngcp", "-r", "2", "srm://srm.swegrid.se/snic/uppnex/test/" + self.test_proj_name + "/", self.verification_proj_folder + "/"]
        print("Downloading files for verification ...")
        self.exec_command(download_cmd)
    
    def unpack(self):
        files_in_verification_folder = os.listdir(self.verification_proj_folder)
        assert len(files_in_verification_folder) == 1
        arch_mssn_folder_name = files_in_verification_folder[0]
        assert re.match("arch_mssn.*", arch_mssn_folder_name)
        self.arch_mssn_folder = os.path.join(self.verification_proj_folder, arch_mssn_folder_name)
        meta_files = self.get_files_in_folder_matching_pattern(self.arch_mssn_folder, ".*\.tar\.meta")
        for meta_file in meta_files:
            meta_file_path = os.path.join(self.arch_mssn_folder, meta_file)
            tar_file_basename = self.rchop(meta_file, ".tar.meta")
            tar_file = "%s.tar" % tar_file_basename
            tar_file_path = os.path.join(self.arch_mssn_folder, tar_file)
            tar_file_first_split_file_path = "%s.split00000" % tar_file_path
            
            if os.path.exists(tar_file_first_split_file_path):
                split_files = self.get_files_in_folder_matching_pattern(self.arch_mssn_folder, "%s\.split\d{5}" % tar_file)
                split_file_paths = []
                for split_file in split_files:
                    split_file_path = os.path.join(self.arch_mssn_folder, split_file)
                    split_file_paths.append(split_file_path)
                    
                split_file_paths.sort()
                
                concat_cmd = ["cat"]
                concat_cmd.extend(split_file_paths)
                concat_cmd.extend([">", tar_file_path])
                concat_cmd_string = " ".join(concat_cmd)
                self.exec_command_string(concat_cmd_string)
                assert os.path.exists(tar_file_path)
                
            untar_cmd = ["tar", "-xvf", tar_file_path, "-C", self.arch_mssn_folder]
            self.exec_command(untar_cmd)
            
        self.unpacked_folder1 = os.path.join(self.arch_mssn_folder, "biologin")
        self.unpacked_folder2 = os.path.join(self.arch_mssn_folder, "biologin2", "24028")
        self.unpacked_folders = [self.unpacked_folder1, self.unpacked_folder2]

    
    # ---- Setup and Teardown functions ----------------------------------------------------

    def setUp(self):

        if os.path.exists(self.drop_folder):
            shutil.rmtree(self.drop_folder)

        self.remove_folders()

        # Remove folders on SweStore:    
        self.rm_recurs_remote("srm://srm.swegrid.se/snic/uppnex/test/" + self.test_proj_name)

        if not os.path.exists(self.drop_folder):
            try:
                os.makedirs(self.drop_folder)
            except:
                print("Folder already exists: %s" % self.drop_folder)    
                
        if not os.path.exists(self.uploadcache_proj_folder):
            try:
                os.makedirs(self.uploadcache_proj_folder)
            except:                        
                print("Folder already exists: %s" % self.uploadcache_proj_folder)    
                
        if not os.path.exists(self.confirm_folder):
            try:
                os.makedirs(self.confirm_folder)
            except:
                print("Folder already exists: %s" % self.confirm_folder)    
                
        if not os.path.exists(self.verification_proj_folder):
            try:
                os.makedirs(self.verification_proj_folder)
            except:
                print("Folder already exists: %s" % self.verification_folder)    

        shutil.copytree(os.path.join(self.test_data_folder_structure, "biologin"), os.path.join(self.drop_folder, "biologin"))
        shutil.copytree(os.path.join(self.test_data_folder_structure, "biologin2"), os.path.join(self.drop_folder, "biologin2"))
        shutil.copytree(os.path.join(self.test_data_folder_structure, "emptyfolder"), os.path.join(self.drop_folder, "emptyfolder"))
        shutil.copyfile(os.path.join(self.test_data_folder_structure, "archiving_state.new"), os.path.join(self.drop_folder, "archiving_state.new"))

    def tearDown(self):
        self.remove_folders()

        # Remove folders on SweStore:    
        self.rm_recurs_remote("srm://srm.swegrid.se/snic/uppnex/test/" + self.test_proj_name)


    # ---- Helper functions ----------------------------------------------------
    
    def exec_command(self, command):
        proc = subprocess.Popen(command, stdout=subprocess.PIPE)
        output = proc.communicate()[0]
        output = string.strip(output)
        return output
    
    def exec_command_string(self, command):
        subprocess.call(command, shell=True)

    def rm_recurs_remote(self, dir_to_remove):
        output = self.exec_command(["ngls", "-r", "0", "-l", dir_to_remove])
        lines = string.split(output, "\n")
        for line in lines:
            if line is not "":
                bits = line.split(" ")
                if len(bits) > 1:
                    item = bits[0]
                    type = bits[1]
                    item_path = os.path.join(dir_to_remove, item)
                    if type == "dir":
                        print("Navigating down in subdir: %s" % item_path)
                        self.rm_recurs_remote(item_path)
                    elif type == "file":
                        # print "Removing file: %s" % filepath
                        self.exec_command(["ngrm", item_path])
        print("No more subfolders here, so deleting folder: %s" % dir_to_remove)
        self.exec_command(["ngrm", dir_to_remove])
    
    def remove_folders(self):
        if os.path.exists(self.proj_folder):
            shutil.rmtree(self.proj_folder)
        
        if os.path.exists(self.uploadcache_folder):
            shutil.rmtree(self.uploadcache_folder)
        
        if os.path.exists(self.verification_folder):
            shutil.rmtree(self.verification_folder)

    def get_files_in_folder_matching_pattern(self, folder, pattern, antipattern=""):
        result_files = []
        for file in os.listdir(folder):
            if (re.match(pattern, file) and antipattern == "") or (re.match(pattern, file) and not re.match(antipattern, file)):
                result_files.append(file)
        return result_files
    
    def rchop(self, thestring, ending):
        if thestring.endswith(ending):
            return thestring[:-len(ending)]
        return thestring

    def folder_content_count(self, folder):
        folder_content = os.listdir(folder)
        folder_content_cnt = len(folder_content)
        return folder_content_cnt
    