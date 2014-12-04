import re, sys, os
import config
import sqlite3 as lite
import ConfigParser

# using convention over configuration 
# the executable is the name of the app
# and the input file is the name of the app + '.in'
apps_dir = config.apps_dir
user_dir = config.user_dir
template_dir = config.template_dir
# end set 

# future feature
#workflow = "login >> start >> confirm >> execute"
class app(object):

#CREATE TABLE apps(appid integer primary key autoincrement, name varchar(20), description varchar(80), category varchar(20), language varchar(20));

    def __init__(self):
        # Connect to DB 
        self.con = None
        try:
            self.con = lite.connect(config.db)
        except lite.Error, e:
            print "Error %s:" % e.args[0]
            sys.exit(1)

    def create(self,name,description,category,language,input_format):
        cur = self.con.cursor()
        cur.execute('insert into apps values (NULL,?,?,?,?,?)',
                   (name,description,category,language,input_format))
        self.con.commit()

    def read(self,appid):
        cur = self.con.cursor()
        (name,description,language,category) = cur.execute('select name,description,language,category from apps where appid=?',(appid,))
        for i in result: print i
        return (name,description,language,category)

    def update(self):
        pass

    def delete(self,appid):
        cur = self.con.cursor()
        cur.execute('delete from apps where appid = (?)',(appid,))
        self.con.commit()

    def deploy(self):
        pass

    def write_html_template(self):
    # need to output according to blocks
        confirm="/{{app}}/confirm"
        f = open('views/'+self.appname+'.tpl', 'w')
        f.write("%include header title='confirm'\n")
        f.write("<body onload=\"init()\">\n")
        f.write("%include navbar\n")
        f.write("<!-- This file was autogenerated from SciPaaS -->\n")
        f.write("<form action=\""+confirm+"\" method=\"post\">\n")
        f.write("<input class=\"start\" type=\"submit\" value=\"confirm\" />\n")
        f.write("<div class=\"tab-pane\" id=\"tab-pane-1\">\n")
        for block in self.blockorder:
            f.write("<div class=\"tab-page\">\n")
            f.write("<h2 class=\"tab\">" + block + "</h2>\n")
            f.write("<table><tbody>\n")
            for param in self.blockmap[block]:
                str = "<tr><td>" + param + ":</td>\n"
                str += "<td>"
                if re.search("(TRUE|FALSE)",self.params[param]):
                    str += "<input type=\"checkbox\" name=\"" + param + "\" "
                    str += "value=\"true\"/>"
                else: 
                    str += "<input type=\"text\" name=\"" + param + "\" "
                    str += "value=\"{{" + param + "}}\"/>"
                str += "</td></tr>\n"
                f.write(str)
            f.write("</tbody></table>\n")
            f.write("</div>\n")
        f.write("</div>\n")
        f.write("</form>\n")
        f.write("%include footer")
        f.close()
        return 1

# user must write their own function for how to write the output file
class namelist(app):
    '''Class for plugging in Fortran apps ...'''
    
    def __init__(self,appname,appid=0):
        self.appname = appname
        self.appid = appid
        self.appdir = apps_dir + os.sep + appname
        self.outfn = appname + '.out'
        self.simfn = appname + '.in'
        self.user_dir = user_dir
        self.params, self.blockmap, self.blockorder = self.read_params()
        self.exe = apps_dir + os.sep + self.appname + os.sep + self.appname

    def write_params(self,form_params,user):
        '''write the input file needed for the simulation'''

        cid = form_params['case_id']
        sim_dir=self.user_dir+os.sep+user+os.sep+self.appname+os.sep+cid+os.sep
        #form_params['data_file_path'] = sim_dir
        # following line is temporary hack just for mendel app
        form_params['data_file_path'] = "'./'"
       
        if not os.path.exists(sim_dir):
            os.makedirs(sim_dir)

        fn = sim_dir + self.simfn

        ## output parameters to output log
        #i = 0
        #for fp in form_params:
        #    i += 1
        #    print i,fp, form_params[fp]

        f = open(fn, 'w')
        # need to know what attributes are in what blocks
        for section in self.blockorder:
            f.write("&%s\n" % section)
            for key in self.blockmap[section]:
                # if the keys are not in the params, it means that
                # the checkboxes were not checked, so add the keys
                # to the form_params here and set the values to False.
                # Also, found that when textboxes get disabled e.g. via JS 
                # they also don't show up in the dictionary.
                if key not in form_params:
                    #print "key not found - inserting:", key
                    form_params[key] = "F"

                # replace checked checkboxes with T value
                #print 'key/value', key, form_params[key]
                form_params[key].replace("'","")
                if form_params[key] == 'on':
                    form_params[key] = "T"

                # detect strings and enclose with single quotes
                m = re.search(r'[a-zA-Z]{2}',form_params[key])
                if m:
                    #if not re.search('[0-9.]*e+[0-9]*|[FT]',m.group()):
                    if not re.search('[0-9].*[0-9]^|[FT]',m.group()):
                        form_params[key] = "'" + form_params[key] + "'"

                f.write(key + ' = ' + form_params[key] + "\n")
            f.write("/\n\n")
        f.close
        return 1

    def read_params(self,user=None,cid=None):
        '''read the namelist file and return as a dictionary'''
        if cid is None or user is None:
            fn = self.appdir
        else:
            fn = self.user_dir+os.sep+user+os.sep+self.appname+os.sep+cid
        # append name of input file to end of string
        fn += os.sep + self.simfn
        params = dict()
        blockmap = dict() 
        blockorder = []
 
        for line in open(fn, 'rU'):
            m = re.search(r'&(\w+)',line) # section title
            n = re.search(r'(\w+)\s?=\s?(.*$)',line) # parameter
            if m:
                section = m.group(1)  
                blockorder += [ m.group(1) ]
            elif n:
                # Delete apostrophes and commas
                val = re.sub(r"[',]", "", n.group(2))
                # Delete Fortran comments and whitespace
                params[n.group(1)] = re.sub(r'\!.*$', "", val).strip()
                # Append to blocks e.g. {'basic': ['case_id', 'mutn_rate']}
                blockmap.setdefault(section,[]).append(n.group(1))
		#print n.group(1), val
        return params, blockmap, blockorder

class ini(app):

    def __init__(self,appname,appid=0):
        self.appname = appname
        self.appid = appid
        self.appdir = apps_dir + os.sep + appname
        self.outfn = appname + '.out'
        self.simfn = appname + '.ini'
        self.user_dir = user_dir
        self.params, self.blockmap, self.blockorder = self.read_params()
        self.exe = apps_dir + os.sep + self.appname + os.sep + self.appname

    def read_params(self,user=None,cid=None):
        '''read the namelist file and return as a dictionary'''
        if cid is None or user is None:
            fn = self.appdir
        else:
            fn = self.user_dir+os.sep+user+os.sep+self.appname+os.sep+cid
        # append name of input file to end of string
        fn += os.sep + self.simfn
        #print 'fn:',fn
        Config = ConfigParser.ConfigParser()
        out = Config.read(fn)
        params = {}
        blockmap = {}
        blockorder = []
        for section in Config.sections():
            options = Config.options(section)
            blockorder += [ section ]
            for option in options:
                try:
                    params[option] = Config.get(section, option)
                    blockmap.setdefault(section,[]).append(option)
                    if params[option] == -1:
                        DebugPrint("skip: %s" % option)
                except:
                    print("exception on %s!" % option)
                    params[option] = None
        #print 'params:',params
        #print 'blockmap:',blockmap
        #print 'blockorder:',blockorder
        return params, blockmap, blockorder

    def write_params(self,form_params,user):
        Config = ConfigParser.ConfigParser()
        cid = form_params['case_id']
        sim_dir=self.user_dir+os.sep+user+os.sep+self.appname+os.sep+cid+os.sep
        if not os.path.exists(sim_dir):
            os.makedirs(sim_dir)
        fn = sim_dir + self.simfn

        # write out parameters to screen
        i = 0
        for fp in form_params:
            i += 1
            print i,fp, form_params[fp]

        # create the ini file
        cfgfile = open(fn,'w')
        for section in self.blockorder:
            Config.add_section(section)
            for key in self.blockmap[section]:
                Config.set(section,key,form_params[key])
        Config.write(cfgfile)
        cfgfile.close()
        return 1
