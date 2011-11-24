#!/usr/bin/python

import sys, os
# Import project specific modules
from model.Application import Application
from optparse import OptionParser

# This is the main file, the one supposed to be executed from the command line


# \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
#  Parse command line options
# \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

parser = OptionParser()
parser.add_option("-a", "--action", dest="action", type="string",
                  help="Choose action to execute, either 'prepare', 'upload' or 'createconfirmfiles'", metavar="ACTION")
parser.add_option("-d", "--upload-delay", dest="delayindays",
                  help="Delay in DAYS, between the move to the upload cache and the upload to SweStore", metavar="DAYS")
parser.add_option("-c", "--config-file", dest="configfile",
                  help="Specify the full path to a file (in the python ConfigParser format) that contains the config to be used.\
                        (Note that command line options will override this).", metavar="CONFIGFILE")

#for config_option in app.config.option_names:
#    parser.add_option("--%s" % config_option, dest=config_option)

(options, args) = parser.parse_args()

# Require that the settings file param is set
if not options.configfile: 
    sys.exit("No settings file specified. Please use the -h flag to view command line options")
if not os.path.isfile(options.configfile): 
    sys.exit("Specified settings file not a valid file!")
# Require that the action parameter is set, otherwise stop the script
if options.action not in ['prepare', 'upload', 'createconfirmfiles']:
    sys.exit("No action specified. Please use the -h flag to view command line options")

app = Application(configfile_path=options.configfile)

#option_list = vars(options)
#for option_name in option_list:
#    option_value = option_list[option_name]
#    #print "Reading cli option: %s = %s" % (option_name, option_value)
#    if type(option_value) in (str, int, bool):
#        app.config.options[option_name] = option_value

#options.



# \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
#  Execute Application
# \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

app.init_action(options.action)
app.run()