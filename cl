#!/usr/bin/env python

import config
import sys
import os

sys.argv[1:]

try:
    if(sys.argv[1] == "n"):
        params = config.read_namelist()
        if config.write_html_template():
		    print "successfully output template"
        config.define_workflow()

    if(sys.argv[1] == "s"):
        os.system("python main.py")

except:
    print "usage: " + sys.argv[0] + " <command>"
    print
    print "list of commands:"
    print "n - create new project"
    print "s - start the web server"
