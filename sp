#!/usr/bin/env python
from scipaas import macaron, config
from scipaas import apps as appmod
from scipaas.model import *
import sys, os, shutil, urllib2
import xml.etree.ElementTree as ET

class Plots(macaron.Model): pass
class Users(macaron.Model): pass
class Apps(macaron.Model): pass

sys.argv[1:]

url = 'https://s3-us-west-1.amazonaws.com/scihub'

def usage():
    buf =  "SciPaaS usage: sp <command> [options]\n\n"
    buf += "commonly used commands:\n"
    buf += "init     initialize a database for scipaas\n"
    buf += "go       start the server\n"
    buf += "create   create a view template for appname (e.g. sp create myapp)\n"
    buf += "search   search for available apps\n"
    buf += "list     list installed or available apps (e.g. sp list [available|installed]) \n"
    buf += "install  install an app\n"
    return buf

if (len(sys.argv) == 1):
    print usage()
    sys.exit()

db = config.db
# make a backup copy if file exists
if(sys.argv[1] == "init"):
    if os.path.isfile(db): 
        shutil.copyfile(db, db+".bak")
# Initializes Macaron
macaron.macaronage(db)

def initdb():
    """Initializes database file"""
    import hashlib

    # Creates tables
    SQL_T_APPS = """CREATE TABLE IF NOT EXISTS apps(
        id integer primary key autoincrement, 
        name varchar(20), description varchar(80), category varchar(20), 
        language varchar(20), input_format, command, preprocess, postprocess)"""

    SQL_T_USERS = """CREATE TABLE IF NOT EXISTS users(
        id integer primary key autoincrement, user varchar(20) unique, 
        passwd varchar(20), email varchar(80))"""

    SQL_T_JOBS = """CREATE TABLE IF NOT EXISTS jobs(
        id integer primary key autoincrement, user text, app text,
        cid text, state char(1), time_submit text, description text,
        np integer)"""

    SQL_T_PLOTS = """CREATE TABLE IF NOT EXISTS plots(
        id integer primary key autoincrement, 
        appid integer,  ptype varchar(80), filename varchar(80), cols varchar(20), 
        line_range varchar(20), title varchar(80), options text, datadef text)""" 
        # foreign key (appid) references apps(appid))

    SQL_T_WALL = """CREATE TABLE wall(
        id integer primary key autoincrement, jid integer, comment varchar(80), 
        foreign key (jid) references jobs)"""

    macaron.execute(SQL_T_USERS)
    macaron.execute(SQL_T_JOBS)
    macaron.execute(SQL_T_APPS)
    macaron.execute(SQL_T_PLOTS)
    macaron.execute(SQL_T_WALL)

    # create a default user/pass as guest/guest
    pw = "guest"
    hashpw = hashlib.sha256(pw).hexdigest()
    u = Users.create(user="guest", passwd=hashpw)
    # following two users are reserved for beaker sessions
    pw = "admin"
    hashpw = hashlib.sha256(pw).hexdigest()
    u = Users.create(user="admin", passwd=hashpw)
    u = Users.create(user="container_file")
    u = Users.create(user="container_file_lock")
    a = Apps.create(name="dna",description="Compute reverse complement, GC content, and codon analysis of given DNA string.",
        category="bioinformatics",language="python",input_format="namelist")
    p = Plots.create(appid=1,type="flot-bar",filename="din.out",col1=1,col2=2,title="Dinucleotides")
    p = Plots.create(appid=1,type="flot-bar",filename="nucs.out",col1=1,col2=2,title="Nucleotides")
    p = Plots.create(appid=1,type="flot-bar",filename="codons.out",col1=1,col2=2,title="Codons")
    macaron.bake()

notyet = "this feature not yet working"

# http://stackoverflow.com/questions/4028697/how-do-i-download-a-zip-file-in-python-using-urllib2
def dlfile(url):
    # Open the url
    try:
        f = urllib2.urlopen(url)
        print "downloading " + url
        # Open our local file for writing
        with open(os.path.basename(url), "wb") as local_file:
            local_file.write(f.read())
    #handle errors
    except urllib2.HTTPError, e:
        print "HTTP Error:", e.code, url
    except urllib2.URLError, e:
        print "URL Error:", e.reason, url

# process command line options
if __name__ == "__main__":
    if(sys.argv[1] == "create"):
        if (len(sys.argv) == 3): 
            i = Apps.select("name=?",[ sys.argv[2] ])
            input_format = i[0].input_format
            print 'input format is:',input_format
            if sys.argv[2]: 
                if input_format == 'namelist':
                    myapp = appmod.namelist(sys.argv[2])
                elif input_format == 'ini':
                    myapp = appmod.ini(sys.argv[2])
                elif input_format == 'xml':
                    myapp = appmod.xml(sys.argv[2])
                elif input_format == 'json':
                    myapp = appmod.json(sys.argv[2])
                else:
                    print "ERROR: input format type not supported:", input_format
            params,_,_ = myapp.read_params()
            if myapp.write_html_template():
                print "successfully output template"
        else:
            print "usage: sp create appname"
    elif (sys.argv[1] == "init"):
        print "creating database " + config.db
        initdb()
    elif (sys.argv[1] == "go"):
        os.system("python scipaas/scipaas.py")
    elif (sys.argv[1] == "search"):
        print notyet
    elif (sys.argv[1] == "install"):
        install_usage = "usage: sp install appname"
        if len(sys.argv) == 3:
            durl = url+'/'+sys.argv[2]+'.zip' 
            print 'durl is:',durl
            dlfile(durl)
        else:
            print install_usage

    elif (sys.argv[1] == "list"):
        list_usage = "usage: sp list [available|installed]"
        if (len(sys.argv) == 3):
            if (sys.argv[2] == "installed"):
                result = Apps.all()
                for r in result:
                    print r.name
            elif (sys.argv[2] == "available"):
                response = urllib2.urlopen(url)
                html = response.read()
                root = ET.fromstring(html)
                for child in root.findall("{http://s3.amazonaws.com/doc/2006-03-01/}Contents"):
                    for c in child.findall("{http://s3.amazonaws.com/doc/2006-03-01/}Key"):
                        (app,ext) = c.text.split(".")
                        print app 
            else:
                print list_usage
        else:
            print list_usage
    else:
        print "ERROR: option not supported"
        sys.exit()

