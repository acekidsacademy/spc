#!/usr/bin/env python

# web framework
from bottle import *
from bottle.ext import sqlite
# database stuff
#import macaron
import sqlite3 as lite
from dal import DAL, Field
# python built-ins
import uuid, hashlib, shutil, string
import random, subprocess, sys, os, re
import cgi
# other SciPaaS modules
import config, uploads, scheduler
import apps as appmod
import plots as plotmod
#from models import *

### ORM/DAL stuff
#install(macaron.MacaronPlugin(config.db))
db2 = DAL('sqlite://storage.sqlite', auto_import=True, migrate=False)
#db2 = models()

### session management configuration ###
from beaker.middleware import SessionMiddleware
USER_ID_SESSION_KEY = 'user_id'
APP_SESSION_KEY = 'app'

session_opts = {
    'session.type': 'file',
    'session.cookie_expires': True, # delete cookies when browser closed
    'session.data_dir': config.user_dir,
    'session.auto': True
}

app = SessionMiddleware(app(), session_opts)
### end session management configuration ###

# sqlite plugin
plugin = ext.sqlite.Plugin(dbfile=config.db)
install(plugin)

# create instance of scheduler
sched = scheduler.scheduler()

pbuffer = ''

users = db2.define_table('users', Field('id','integer'), 
                                  Field('user', 'string'), 
                                  Field('passwd','string'))
apps = db2.define_table('apps', Field('id','integer'),
                                Field('name','string'),
                                Field('description','string'),
                                Field('category','string'),
                                Field('language','string'),
                                Field('input_format','string'))
jobs = db2.define_table('jobs', Field('id','integer'),
                                Field('user','string'),
                                Field('app','string'),
                                Field('cid','string'),
                                Field('state','string'),
                                Field('time_submit','string'),
                                Field('description','string'))
plots = db2.define_table('plots', Field('id','integer'),
                                  Field('appid','integer'),
                                  Field('type','string'),
                                  Field('filename','string'),
                                  Field('col1','integer'),
                                  Field('col2','integer'),
                                  Field('title','string'))
wall = db2.define_table('wall', Field('id','integer'),
                                Field('jid','integer'),
                                Field('comment','string'))

@post('/<app>/confirm')
def confirm_form(app):
    global user
    # if case_id not in form will throw error, but just ignore it
    # as some apps will not use case_id
    try:
        #cid = request.forms['case_id']
        cid = str(uuid.uuid4())[:6]
    except: 
        return "ERROR: problem with template... case_id not in form"
    print 'cid:%s,app:%s' % (cid, app)
    # this is only valid for mendel or similar programs that use a case_id 
    # parameter have to fix this in the future
    request.forms['case_id'] = cid 
    myapps[app].write_params(request.forms,user)
    inputs = slurp_file(app,cid,myapps[app].simfn,user)
    # convert html tags to entities (e.g. < to &lt;)
    inputs = cgi.escape(inputs)
    params = { 'cid': cid, 'inputs': inputs, 'app': app, 'user': user }
    try:
        return template('confirm', params)
    except:
        return 'ERROR: failed to write parameters to file'

@post('/<app>/<cid>/execute')
def execute(db,app,cid):
    global user
    #cid = request.forms.get('cid')
    #print 'execute:',app,cid
    params = {}
    try:
        params['cid'] = cid
        params['app'] = app
        params['user'] = user
        sched.qsub(app,cid,user)
        #redirect("/jobs/"+app+"?cid="+cid)
        redirect("/jobs?app="+app+"&cid="+cid)
    except OSError, e:
        print >>sys.stderr, "Execution failed:", e
        params = { 'cid': cid, 'output': pbuffer, 'app': app, 'user': user, 'err': e }
        return template('error',params)

@get('/output')
def output():
    global user
    app = request.query.app
    cid = request.query.cid
    try:
        if re.search("/",cid):
            (u,c) = cid.split("/") 
        else:
            u = user
            c = cid
        output = slurp_file(app,c,myapps[app].outfn,u)
        params = { 'cid': cid, 'output': output, 'app': app, 'user': u }
        return template('output', params)
    except:
        params = { 'app': app, 'err': "Couldn't read input file. Check casename." } 
        return template('error', params)

@get('/inputs')
def inputs():
    global user
    app = request.query.app
    cid = request.query.cid
    try:
        if re.search("/",cid):
            (u,c) = cid.split("/") 
        else:
            u = user
            c = cid
        inputs = slurp_file(app,c,myapps[app].simfn,u)
        params = { 'cid': cid, 'inputs': inputs, 'app': app, 'user': u }
        return template('inputs', params)
    except:
        params = { 'app': app, 'err': "Couldn't read input file. Check casename." } 
        return template('error', params)

def slurp_file(app,cid,filename,user):
    run_dir = myapps[app].user_dir+os.sep+user+os.sep+myapps[app].appname+os.sep+cid
    fn = run_dir + os.sep + filename
    try:
        f = open(fn,'r')
        inputs = f.read()
        f.close()
        return inputs
    except IOError:
        return("ERROR: the file cannot be opened or does not exist.\nSelect a case id first.")

@get('/<app>/<cid>/tail')
def tail(app,cid):
    global user
    num_lines = 30
    run_dir = myapps[app].user_dir+os.sep+user+os.sep+myapps[app].appname+os.sep+cid
    ofn = run_dir + os.sep + myapps[app].outfn
    f = open(ofn,'r')
    output = f.readlines()
    myoutput = output[len(output)-num_lines:]
    xoutput = ''.join(myoutput)
    f.close()
    params = { 'cid': cid, 'output': xoutput, 'app': app, 'user': user }
    return template('output', params)

@route('/')
def root():
    return template('overview')

@route('/jobs')
def show_jobs(db):
    if not authorized(): redirect('/login')
    #if app not in myapps: redirect('/apps')
    global user
    cid = request.query.cid
    app = request.query.app
    result = db2(users.user==user).select(jobs.ALL)
    params = {}
    params['cid'] = cid
    params['app'] = app
    params['user'] = user
    return template('jobs', params, rows=result)

@get('/wall')
def get_wall(db):
    """Return the records from the wall table."""
    if not authorized(): redirect('/login')
    global user
    cid = request.query.cid
    app = request.query.app
    # note: =~ means sort by descending order
    result = db2(jobs.id==wall.jid).select(orderby=~wall.id)
    params = {}
    params['cid'] = cid
    params['app'] = app
    params['user'] = user
    return template('wall', params, rows=result)

@post('/wall')
def post_wall(db):
    if not authorized(): redirect('/login')
    app = request.forms.app
    cid = request.forms.cid
    jid = request.forms.jid
    comment = request.forms.comment
    # save comment to db
    wall.insert(jid=jid, comment=comment)
    db2.commit()
    # get all wall comments
    result = db2().select(wall.ALL)
    params = {}
    params['cid'] = cid
    params['app'] = app
    params['user'] = user
    redirect('/wall')

@route('/jobs/delete/<jid>')
def delete_job(jid):
    sched.qdel(jid)
    redirect("/jobs")

# this doesnt work.. needs to be run as a separate thread
@get('/jobs/stop/<app>')
def stop_job(db,app):
    os.system("killall " + app)
    redirect("/jobs")

@route('/<app>')
def show_app(app):
    if not authorized(): redirect('/login')
    global user, myapps
    # set a session variable to keep track of the current app
    s = request.environ.get('beaker.session')
    s[APP_SESSION_KEY] = app
    # parameters for return template
    params = myapps[app].params
    params['cid'] = '' 
    params['app'] = app
    params['user'] = user
    return template(config.apps_dir+os.sep+app, params)

@get('/login')
@get('/login/<referrer>')
def get_login(referrer=''):
    return template('login',{'referrer': referrer})

@get('/logout')
def logout():
    s = request.environ.get('beaker.session')
    s.delete()
    redirect('/')

@route('/static/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root='static')

@get('/favicon.ico')
def get_favicon():
    return server_static('favicon.ico')

@post('/login')
def post_login(db):
    global user
    s = request.environ.get('beaker.session')
    user = users(user=request.forms.get('user'))
    pw = request.forms.passwd
    err = "<p>Login failed: wrong username or password</p>"
    # if password matches, set the USER_ID_SESSION_KEY
    hashpw = hashlib.sha256(pw).hexdigest()
    try:
        if hashpw == user.passwd:
            # set global user and session key
            user = s[USER_ID_SESSION_KEY] = user.user
        else:
            return err
    except:
        return err
    # if referred to login from another page redirect to referring page
    referrer = request.forms.referrer
    if referrer: redirect('/'+referrer)
    else: redirect('/')

@get('/register')
def get_register():
    return template('register')

@post('/register')
def post_register():
    user = request.forms.user
    pw1 = request.forms.password1
    pw2 = request.forms.password2
    if pw1 == pw2:
        hashpw = hashlib.sha256(pw1).hexdigest()
        users.insert(user=user, passwd=hashpw)
        db2.commit()
        redirect('/login')
    else:
        return template('register')

@post('/check_user')
def check_user():
    """This is the server-side AJAX function to check if a username exists in the DB."""
    this = users(user=request.forms.user)
    # return booleans as strings here b/c they get parsed by JavaScript
    if this: return 'true'
    else: return 'false'

@get('/apps')
def showapps():
    redirect("/apps/show/name")

@get('/apps/load')
def load_apps(db):
    # this needs to be moved into apps.py in the future
    global myapps, default_app
    # Connect to DB 
    try:
        result = db2().select(apps.ALL)
    except e:
        print "Error %s:" % e.args[0]
        print "MAKE SURE DATABASE EXIST."
        print "If running for the first time, run \"sp init\" to create a db"
        sys.exit(1)
    myapps = {}
    for row in result:   
        name = row['name']
        appid = row['id']
        input_format = row['input_format']
        #print 'loading: %s (id: %s)' % (name,appid)
        print 'loading: %s' % (name)
        if(input_format=='namelist'):
            myapp = appmod.namelist(name,appid)
        elif(input_format=='ini'):
            myapp = appmod.ini(name,appid)
        elif(input_format=='xml'):
            myapp = appmod.xml(name,appid)
        elif(input_format=='json'):
            myapp = appmod.json(name,appid)
        else:
            return 'ERROR: input_format ',input_format,' not supported'
        myapps[name] = myapp
    default_app = name # simple soln - use last app read from DB
    return 0

@get('/apps/show/<sort>')
def getapps(db,sort="name"):
    if not authorized(): redirect('/login')
    result = db2().select(apps.ALL)
    return template('apps', rows=result)

@get('/apps/add')
def create_app_form():
    if not authorized(): redirect('/login')
    return static_file('addapp.html', root='static')

@post('/apps/add')
def addapp():
    # get data from form
    appname = request.forms.get('appname')
    description = request.forms.get('description')
    category = request.forms.get('category')
    language = request.forms.get('language')  
    input_format = request.forms.get('input_format')
    # put in db
    a = apps.app()
    a.create(appname,description,category,language,input_format)
    redirect("/apps/show/name")

@post('/apps/create_view')
def create_view():
    appname = request.forms.get('appname')
    params,_,_ = myapp.read_params()
    if myapp.write_html_template():
        return "SUCCESS: successfully output template"
    else:
        return "ERROR: there was a problem when creating view"

#@post('/apps/delete/<appid>')
#def delete_app(appid):
#    a = apps.app()
#    a.delete(appid)
#    redirect("/apps/show/name")

@get('/apps/edit/<appid>')
def edit_app(appid):
    return 'SORRY - this function has not yet been implemented'
    a = apps.app()
    (name,description,category,language) = a.read(appid)
    params = {'name': name, 'description': description, 'category': category, 'language': language }
    return template(app_edit, params)

@get('/start')
def getstart():
    global user
    try:
        app = request.query.app
        if myapps[app].appname not in myapps: redirect('/apps')
        cid = request.query.cid
        if re.search("/",cid):
            (u,cid) = cid.split("/") 
        else:
            u = user
        params = myapps[app].params
        if cid is '':
            params = myapps[app].params
        else:
            params,_,_ = myapps[app].read_params(u,cid)
        params['cid'] = cid
        params['app'] = app
        params['user'] = u
        return template('apps/' + myapps[app].appname, params)
    except:
        params = {'err': "must first select an app to run by clicking apps button."}
        return template('error', params)
        #redirect("/apps/show/name")

@get('/<app>/list')
def list(db,app):
    global user
    str = ''
    for case in os.listdir(myapps[app].user_dir+os.sep+user+os.sep+app):
        str += '<form action="/'+app+'/delete/'+case+'">'
        str += '<a onclick="set_cid(\'' + case + '\')">' + case + '</a>'
        str += '<input type="image" src="/static/trash_can.gif"></form>\n'
    params = { 'content': str }
    params['cid'] = request.forms.get('cid')
    params['app'] = app
    params['user'] = user
    return template('list', params)

@get('/plots')
def get_plots(db):
    global user
    #try:
    app = request.query.app
    if myapps[app].appname not in myapps: redirect('/apps')
    if not authorized(): redirect('/login')
    result = db2(apps.id==plots.appid).select()
    params = { 'app': app, 'cid': request.query.cid, 'user': user } 
    return template('plots', params, rows=result)
    #except:
    #    params = {'err': "must first select an app to plot by clicking apps button"}
    #    return template('error', params)

@get('/plots/delete/<pltid>')
def delete_plot(db,pltid):
    app = request.query.app
    cid = request.query.cid
    p = plotmod.plot()
    p.delete(pltid)
    redirect ('/plots?app='+app)

@post('/plots/create')
def create_plot():
    app = request.forms.get('app')
    cid = request.forms.get('cid')
    p = plotmod.plot()
    r = request
    p.create(myapps[app].appid,r.forms['ptype'],r.forms['fn'],r.forms['col1'],r.forms['col2'],r.forms['title'])
    redirect ('/plots?app='+app+'&cid='+cid)

@get('/plot/<pltid>')
def plot_interface(pltid):
    app = request.query.app
    cid = request.query.cid

    if re.search("/",cid):
        (u,c) = cid.split("/") 
    else:
        u = user
        c = cid

    p = plotmod.plot()
    (plottype,plotfn,col1,col2,title) = p.read(app,pltid)
    params = {'app': app, 'cid': cid, 'user': u} 

    # if plot not in DB return error
    if plottype is None:
        params = { 'cid': cid, 'app': app, 'user': u }
        params['err'] = "Sorry! This app does not support plotting capability"
        return template('error', params)

    if plottype == 'bar':
        bars = 'true'
    else:
        bars = 'false'
     
    if plottype == 'categories': 
        tfn = 'plot-cat'
    else:
        tfn = 'plot-line' 

    sim_dir = myapps[app].user_dir+os.sep+u+os.sep+app+os.sep+c+os.sep
    #if re.search(r'^\s*$', cid):
    if not cid:
        params['err']="No case id specified. First select a case id from the list of jobs."
        return template('error', params)
    else:
        plotfn = re.sub(r"<cid>", c, plotfn)
        p = plotmod.plot()
        data = p.get_data(sim_dir + plotfn,col1,col2)
        ticks = p.get_ticks(sim_dir + plotfn,col1,col2)
        params = { 'cid': cid, 'data': data, 'app': app, 'user': u, 'ticks': ticks,
                   'title': title, 'bars': bars }
        return template(tfn, params)

@get('/<app>/<cid>/data/<pltid>')
def get_data():
    pass

@get('/<app>/<cid>/monitor')
def monitor(app,cid):
    global user
    params = { 'cid': cid, 'app': app, 'user': user }
    return template('monitor', params)

@post('/apps/upload')
def do_upload():
    #appname    = request.forms.get('appname')
    upload     = request.files.get('upload')
    name, ext = os.path.splitext(upload.filename)
    # we're not inputting appname yet so hold off on this check
    #if not name == appname:
    #    return 'ERROR: appname does not equal upload filename... try again'
    if ext not in ('.zip','.txt'):
        return 'ERROR: File extension not allowed.'
    try:
        save_path_dir = apps.apps_dir + os.sep + name
        save_path = save_path_dir + ext
        if os.path.isfile(save_path):
            return 'ERROR: zip file exists already. Please remove first.'
        upload.save(save_path)
        # before unzip file check if directory exists
        if os.path.isdir(save_path_dir):
            msg = 'ERROR: app already exists. Please change name.'
        else:
            u = uploads.uploader()
            u.unzip(save_path)
            msg = u.verify(save_path_dir,name)
        # remove zip file
        os.remove(save_path)
        return msg
    except IOError:
        return "IOerror:", IOError
        raise
    else:
        return "ERROR: must be already a file"

def authorized():
    '''Return True if user is already logged in, False otherwise'''
    global user
    s = request.environ.get('beaker.session')
    s[USER_ID_SESSION_KEY] = s.get(USER_ID_SESSION_KEY,False)
    if not s[USER_ID_SESSION_KEY]: 
        return False
    else: 
        user = s[USER_ID_SESSION_KEY]
        return True

#@error(500)
#def error500(error):
#   return "Sorry, there was a 500 server error: " + str(error)

if __name__ == "__main__":
    db = lite.connect(config.db)
    load_apps(db)
    run(app=app, host='0.0.0.0', port=8081, debug=True)
