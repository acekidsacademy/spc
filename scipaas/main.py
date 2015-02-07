#!/usr/bin/env python

# web framework
from bottle import *
# data access layer
from gluon import DAL, Field
# python built-ins
import uuid, hashlib, shutil, string
import random, subprocess, sys, os, re
import cgi, urllib2, json, smtplib
# other SciPaaS modules
import config, uploads, scheduler, process
import apps as appmod
import plots as plotmod
import aws as awsmod
from model import *

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

# create instance of scheduler
sched = scheduler.scheduler()

pbuffer = ''

@post('/<app>/confirm')
def confirm_form(app):
    global user
    cid = str(uuid.uuid4())[:6]
    # pass the case_id to be used by the program input parameters,
    # if case_id is defined in the input deck it will be used
    # otherwise it is ignored
    request.forms['case_id'] = cid 
    myapps[app].write_params(request.forms,user)
    # read the file 
    run_dir = myapps[app].user_dir+os.sep+user+os.sep+myapps[app].appname+os.sep+cid
    fn = run_dir + os.sep + myapps[app].simfn
    inputs = slurp_file(fn)
    # convert html tags to entities (e.g. < to &lt;)
    inputs = cgi.escape(inputs)
    params = { 'cid': cid, 'inputs': inputs, 'app': app, 'user': user, 'apps': myapps.keys() }
    try:
        return template('confirm', params)
    except:
        return 'ERROR: failed to write parameters to file'

@post('/<app>/<cid>/execute')
def execute(app,cid):
    global user
    #cid = request.forms.get('cid')
    #print 'execute:',app,cid
    params = {}

    try:
        if myapps[app].preprocess:
            run_params,_,_ = myapps[app].read_params(user,cid) 
            processed_inputs = process.preprocess(run_params,myapps[app].preprocess)
            sim_dir = myapps[app].user_dir+os.sep+user+os.sep+app+os.sep+cid+os.sep+myapps[app].preprocess
            f = open(sim_dir,'w') 
            f.write(processed_inputs)
            f.close()
    except:
        pass

    try:
        params['cid'] = cid
        params['app'] = app
        params['user'] = user
        sched.qsub(app,cid,user)
        #redirect("/jobs?app="+app+"&cid="+cid)
        redirect("/monitor?app="+app+"&cid="+cid)
    except OSError, e:
        print >>sys.stderr, "Execution failed:", e
        params = { 'cid': cid, 'output': pbuffer, 'app': app, 'user': user, 'err': e, 
                   'apps': myapps.keys() }
        return template('error',params)

@get('/more')
def more():
    """given a form with the attribute plotpath, output the file to the browser"""
    global user
    app = request.query.app
    cid = request.query.cid
    filepath = request.query.filepath
    contents = slurp_file(filepath)
    params = { 'cid': cid, 'contents': contents, 'app': app, 'user': user, 'fn': filepath,
               'apps': myapps.keys() }
    return template('more', params)

@get('/output')
def output():
    global user
    app = request.query.app
    cid = request.query.cid
    check_user_var()
    try:
        if re.search("/",cid):
            (u,c) = cid.split("/") 
        else:
            u = user
            c = cid
        run_dir = myapps[app].user_dir+os.sep+u+os.sep+myapps[app].appname+os.sep+c
        fn = run_dir + os.sep + myapps[app].outfn
        output = slurp_file(fn)
        params = { 'cid': cid, 'contents': output, 'app': app, 'user': u, 'fn': fn,
                   'apps': myapps.keys() }
        return template('more', params)
    except:
        params = { 'app': app, 'err': "Couldn't read input file. Check casename." } 
        return template('error', params)

@get('/inputs')
def inputs():
    global user
    app = request.query.app
    cid = request.query.cid
    check_user_var()
    try:
        if re.search("/",cid):
            (u,c) = cid.split("/") 
        else:
            u = user
            c = cid
        run_dir = myapps[app].user_dir+os.sep+u+os.sep+myapps[app].appname+os.sep+c
        fn = run_dir + os.sep + myapps[app].simfn
        inputs = slurp_file(fn)
        params = { 'cid': cid, 'contents': inputs, 'app': app, 'user': u, 'fn': fn,
                   'apps': myapps.keys() }
        return template('more', params)
    except:
        params = { 'app': app, 'err': "Couldn't read input file. Check casename." } 
        return template('error', params)

def slurp_file(path):
    """read file given by path and return the contents of the file"""
    try:
        f = open(path,'r')
        data = f.read()
        f.close()
        return data
    except IOError:
        return("ERROR: the file cannot be opened or does not exist.\nSelect a case id first.")

@get('/<app>/<cid>/tail')
def tail(app,cid):
    global user
    check_user_var()
    num_lines = 30
    run_dir = myapps[app].user_dir+os.sep+user+os.sep+myapps[app].appname+os.sep+cid
    ofn = run_dir + os.sep + myapps[app].outfn
    if os.path.exists(ofn):
        f = open(ofn,'r')
        output = f.readlines()
        myoutput = output[len(output)-num_lines:]
        xoutput = ''.join(myoutput)
        f.close()
    else:
        xoutput = 'waiting to start...'
    params = { 'cid': cid, 'contents': xoutput, 'app': app, 'user': user, 'fn': ofn,
               'apps': myapps.keys() }
    return template('more', params)

@get('/')
def root():
    if not authorized(): redirect('/login')
    return template('overview')

@get('/jobs')
def show_jobs():
    if not authorized(): redirect('/login')
    #if app not in myapps: redirect('/apps')
    global user
    cid = request.query.cid
    app = request.query.app
    check_user_var()
    result = db(jobs.user==user).select()
    params = {}
    params['cid'] = cid
    params['app'] = app
    params['user'] = user
    params['apps'] = myapps.keys()
    return template('jobs', params, rows=result)

@get('/aws')
def get_aws():
    if not authorized(): redirect('/login')
    #if app not in myapps: redirect('/apps')
    global user
    cid = request.query.cid
    app = request.query.app
    creds = db().select(db.aws_credentials.ALL)
    # look for aws instances registered by the current user
    # which means first need to get the uid
    uid = db(users.user==user).select(users.id)[0]
    instances = db(aws_instances.ownerid==uid).select()
    params = {}
    params['cid'] = cid
    params['app'] = app
    params['user'] = user
    params['apps'] = myapps.keys()
    if request.query.status:
        params['status'] = request.query.status
    return template('aws',params,creds=creds,instances=instances)

def aws_conn(id):
    """create a connection to the EC2 machine and return the handle"""
    creds = db(db.aws_credentials.id==id).select()[0]
    account_id = creds['account_id']
    secret = creds['secret']
    key = creds['key']
    instances = db(db.aws_instances.id==id).select()[0]
    instance = instances['instance']
    region = instances['region']
    rate = instances['rate']
    return awsmod.ec2(key,secret,account_id,instance,region,rate)

@get('/aws/status/<aid>')
def aws_status(aid):
    if not authorized(): redirect('/login')
    global user
    cid = request.query.cid
    app = request.query.app
    params = {}
    params['aid'] = aid
    params['cid'] = cid
    params['app'] = app
    params['user'] = user
    params['apps'] = myapps.keys()
    a = aws_conn(aid)
    status = a.status()
    status['uptime'] = a.uptime(status['launch_time'])
    status['charge since last boot'] = a.charge(status['uptime'])
    return template('aws_status',params,status=status)

@get('/aws/start/<aid>')
def aws_start(aid):
    if not authorized(): redirect('/login')
    global user
    cid = request.query.cid
    app = request.query.app
    params = {}
    params['aid'] = aid
    params['cid'] = cid
    params['app'] = app
    params['user'] = user
    params['apps'] = myapps.keys()
    a = aws_conn(aid)
    a.start()
    time.sleep(5) # takes a few seconds for the status to change on the Amazon end
    status = a.status()
    return template('aws_status',params,status=status)

@get('/aws/stop/<aid>')
def aws_stop(aid):
    if not authorized(): redirect('/login')
    global user
    cid = request.query.cid
    app = request.query.app
    params = {}
    params['aid'] = aid
    params['cid'] = cid
    params['app'] = app
    params['user'] = user
    params['apps'] = myapps.keys()
    a = aws_conn(aid)
    a.stop()
    time.sleep(5) # takes a few seconds for the status to change on the Amazon end
    return template('aws_status',params,status=a.status())

@get('/wall')
def get_wall():
    """Return the records from the wall table."""
    if not authorized(): redirect('/login')
    global user
    cid = request.query.cid
    app = request.query.app
    # note: =~ means sort by descending order
    result = db(jobs.id==wall.jid).select(orderby=~wall.id)
    params = {}
    params['cid'] = cid
    params['app'] = app
    params['user'] = user
    params['apps'] = myapps.keys()
    return template('wall', params, rows=result)

@post('/wall')
def post_wall():
    if not authorized(): redirect('/login')
    app = request.forms.app
    cid = request.forms.cid
    jid = request.forms.jid
    comment = request.forms.comment
    # save comment to db
    wall.insert(jid=jid, comment=comment)
    db.commit()
    # get all wall comments
    result = db().select(wall.ALL)
    params = {}
    params['cid'] = cid
    params['app'] = app
    params['user'] = user
    redirect('/wall')

@get('/wall/delete/<wid>')
def delete_wall_item(wid):
    app = request.query.app
    cid = request.query.cid
    del db.wall[wid]
    db.commit()
    redirect ('/wall?app='+app+'&cid='+cid)

@get('/jobs/delete/<jid>')
def delete_job(jid):
    app = request.query.app
    cid = request.query.cid
    path = myapps[app].user_dir+os.sep+user+os.sep+app+os.sep+cid+os.sep
    shutil.rmtree(path)
    sched.qdel(jid)
    redirect("/jobs")

# this doesnt work.. needs to be run as a separate thread
@get('/jobs/stop/<app>')
def stop_job(app):
    os.system("killall " + app)
    redirect("/jobs")

@get('/<app>')
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
    params['apps'] = myapps
    return template(config.apps_dir+os.sep+app, params)

@get('/login')
@get('/login/<referrer>')
def get_login(referrer=''):
    return template('login',{'referrer': referrer})

@get('/logout')
def logout():
    s = request.environ.get('beaker.session')
    s.delete()
    redirect('/login')

@get('/static/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root='static')

@get('/user_data/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root='user_data')

@get('/favicon.ico')
def get_favicon():
    return server_static('favicon.ico')

@post('/login')
def post_login():
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
    else: redirect('/apps')

@get('/register')
def get_register():
    return template('register')

@post('/register')
def post_register():
    user = request.forms.user
    pw1 = request.forms.password1
    pw2 = request.forms.password2
    email = request.forms.email
    if pw1 == pw2:
        hashpw = hashlib.sha256(pw1).hexdigest()
        users.insert(user=user, passwd=hashpw, email=email)
        db.commit()
        # email user
        try:
            server = smtplib.SMTP('localhost')
            message = user + " just registered to scipaas " + email
            server.sendmail('admin@scipaas.com', ['ycompute@gmail.com'], message)
            server.quit()
            redirect('/login')
        except:
            return "ERROR: SMTP server not setup on this machine"
    else:
        return template('register')

@post('/check_user')
def check_user():
    user = request.forms.user
    """This is the server-side AJAX function to check if a username exists in the DB."""
    # return booleans as strings here b/c they get parsed by JavaScript
    try:
        this = db(users.user==user).select(users.id)[0]
        return 'true'
    except:
        return 'false'

def check_user_var():
    # this check is because user is global var when restarting scipaas
    # user does not exist so return... need to implement better solution
    # such as using a session variable to check for user
    try: user
    except: redirect('/apps')
    return True

@get('/apps')
def showapps():
    if not authorized(): redirect('/login')
    result = db().select(apps.ALL)
    params = { 'apps': myapps.keys() }
    return template('apps', params, rows=result)

@get('/apps/load')
def load_apps():
    # this needs to be moved into apps.py in the future
    global myapps, default_app
    # Connect to DB 
    #try:
    result = db().select(apps.ALL)
    #except:
    #    print "Error: MAKE SURE DATABASE EXIST."
    #    print "If running for the first time, run \"sp init\" to create a db"
    #    sys.exit(1)
    myapps = {}
    for row in result:   
        name = row['name']
        appid = row['id']
        preprocess = row['preprocess']
        postprocess = row['postprocess']
        input_format = row['input_format']
        print 'loading: %s (id: %s)' % (name,appid)
        #print 'loading: %s' % (name)
        if(input_format=='namelist'):
            myapp = appmod.namelist(name,appid)
        elif(input_format=='ini'):
            myapp = appmod.ini(name,appid,preprocess,postprocess)
        elif(input_format=='xml'):
            myapp = appmod.xml(name,appid)
        elif(input_format=='json'):
            myapp = appmod.json(name,appid)
        else:
            return 'ERROR: input_format ',input_format,' not supported'
        myapps[name] = myapp
    default_app = name # simple soln - use last app read from DB
    return 0

#@get('/apps/show/<sort>')
#def getapps(sort="name"):
#    if not authorized(): redirect('/login')
#    result = db().select(apps.ALL)
#    return template('apps', rows=result)

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
    command = request.forms.get('command')
    preprocess = request.forms.get('preprocess')
    postprocess = request.forms.get('postprocess')
    # put in db
    a = appmod.app()
    a.create(appname,description,category,language,input_format,command,preprocess,postprocess)
    redirect("/apps")

@post('/apps/create_view')
def create_view():
    appname = request.forms.get('appname')
    params,_,_ = myapp.read_params()
    if myapp.write_html_template():
        return "SUCCESS: successfully output template"
    else:
        return "ERROR: there was a problem when creating view"

# this is dangerous... needs to be POST not GET
@get('/apps/delete/<appid>')
def delete_app(appid):
    a = appmod.app()
    a.delete(appid)
    redirect("/apps")

@get('/apps/edit/<appid>')
def edit_app(appid):
    return 'SORRY - this function has not yet been implemented'
    #a = appmod.app()
    #(name,description,category,language) = a.read(appid)
    #params = {'name':name, 'description':description, 'category':category, 'language':language }
    #return template(app_edit, params)

@get('/start')
def getstart():
    global user
    check_user_var()
    #try:
    app = request.query.app
    if myapps[app].appname not in myapps: redirect('/apps')
    cid = request.query.cid
    if re.search("/",cid):
        (u,cid) = cid.split("/") 
    else:
        u = user
    params = myapps[app].params
    # if no valid casename read default parameters
    if not re.search("[a-z]",cid):
        params = myapps[app].params
    else: # read parameters from file
        params,_,_ = myapps[app].read_params(u,cid)
    params['cid'] = cid
    params['app'] = app
    params['user'] = u
    params['apps'] = myapps.keys()
    return template('apps/' + myapps[app].appname, params)
    #except:
    #    params = {'err': "whoops there was a problem... start by clicking apps button"}
    #    return template('error', params)

@get('/files')
def list_files():
    global user
    cid = request.query.cid
    app = request.query.app
    path = request.query.path
    check_user_var()
    if re.search("/",cid):
        (u,cid) = cid.split("/") 
    else:
        u = user
    if not path:
        path = myapps[app].user_dir+os.sep+u+os.sep+app+os.sep+cid

    case_path = myapps[app].user_dir+os.sep+u+os.sep+app
        
    binary_extensions = ['.bz2','.gz','.xz','.zip']
    image_extensions = ['.png','.gif','.jpg']
    str = '<table>'
    for fn in os.listdir(path):
        this_path = path + os.sep + fn
        _, ext = os.path.splitext(this_path)
        str += '<tr>'
        #str += '<td><form action="/'+app+'/delete/'+fn+'">'
        #str += '<input type="image" src="/static/images/trash_can.gif"></form></td>\n'
        str += '<td>'
        if os.path.isdir(this_path): 
            str += '<a href="/files?app='+app+'&cid='+cid+'&path='+this_path+'">'+fn+'/</a>'
        elif ext in binary_extensions:
            str += '<a href="'+this_path+'">'+fn+'</a>'
        elif ext in image_extensions:
            str += '<a href="'+this_path+'"><img src="'+this_path+'" width=100><br>'+fn+'</a>'
        else:
            str += '<a href="/more?app='+app+'&cid='+cid+'&filepath='+path+os.sep+fn+'">'+fn+'</a>'
        str += '</td></tr>\n'
    str += '</table>'
    params = { 'content': str }
    params['cid'] = cid
    params['app'] = app
    params['user'] = u
    params['apps'] = myapps.keys()
    params['cases'] = '<a href="/files?app='+app+'&cid='+cid+'&path='+case_path+'">cases</a>'
    return template('files', params)

#@get('/<app>/list')
#def list(app):
#    global user
#    str = ''
#    for case in os.listdir(myapps[app].user_dir+os.sep+user+os.sep+app):
#        str += '<form action="/'+app+'/delete/'+case+'">'
#        str += '<a onclick="set_cid(\'' + case + '\')">' + case + '</a>'
#        str += '<input type="image" src="/static/images/trash_can.gif"></form>\n'
#    params = { 'content': str }
#    params['cid'] = request.forms.get('cid')
#    params['app'] = app
#    params['user'] = user
#    return template('list', params)

@get('/plots/edit')
def editplot():
    global user
    #try:
    app = request.query.app
    cid = request.query.cid
    check_user_var()
    if not authorized(): redirect('/login')
    if app not in myapps: redirect('/apps')
    query = (apps.id==plots.appid) & (apps.name==app)
    result = db(query).select()
    params = { 'app': app, 'cid': cid, 'user': user, 'apps': myapps.keys() } 
    return template('plots/edit', params, rows=result)
    #except:
    #    params = {'err': "must first select an app to plot by clicking apps button"}
    #    return template('error', params)

@get('/plots/delete/<pltid>')
def delete_plot(pltid):
    app = request.query.app
    cid = request.query.cid
    del db.plots[pltid]
    db.commit()
    redirect ('/plots/edit?app='+app+'&cid='+cid)

@get('/plots/datasource/<pltid>')
def get_datasource(pltid):
    global user
    app = request.query.app
    cid = request.query.cid
    check_user_var()
    if myapps[app].appname not in myapps: redirect('/apps')
    if not authorized(): redirect('/login')
    result = db(datasource.pltid==pltid).select()
    params = { 'app': app, 'cid': cid, 'user': user, 'pltid': pltid, 'rows': result,
               'apps': myapps.keys() } 
    return template('plots/datasource', params, rows=result)

@post('/plots/datasource_add')
def add_datasource():
    app = request.forms.get('app')
    cid = request.forms.get('cid')
    pltid = request.forms.get('pltid')
    r = request.forms
    datasource.insert(pltid=pltid, filename=r['fn'], cols=r['cols'], line_range=r['line_range'],
                      label=r['label'], ptype=r['ptype'], color=r['color'])
    db.commit()
    redirect ('/plots/datasource/'+pltid+'?app='+app+'&cid='+cid)

@post('/plots/datasource_delete')
def delete_plot():
    app = request.forms.get('app')
    cid = request.forms.get('cid')
    pltid = request.forms.get('pltid')
    dsid = request.forms.get('dsid')
    del db.datasource[dsid]
    db.commit()
    redirect ('/plots/datasource/'+pltid+'?app='+app+'&cid='+cid)

@post('/plots/create')
def create_plot():
    app = request.forms.get('app')
    cid = request.forms.get('cid')
    r = request
    plots.insert(appid=myapps[app].appid,ptype=r.forms['ptype'],title=r.forms['title'],options=r.forms['options'],datadef=r.forms['datadef'])
    db.commit()
    redirect ('/plots/edit?app='+app+'&cid='+cid)

@get('/plot/<pltid>')
def plot_interface(pltid):
    app = request.query.app
    cid = request.query.cid
    check_user_var()

    if not cid:
        params['err']="No case id specified. First select a case id from the list of jobs."
        return template('error', params)

    if re.search("/",cid):
        (u,c) = cid.split("/") 
    else:
        u = user
        c = cid

    sim_dir = myapps[app].user_dir+os.sep+u+os.sep+app+os.sep+c+os.sep

    # use pltid of 0 to trigger finding the first pltid for the current app
    if int(pltid) == 0:
        query = (apps.id==plots.appid) & (apps.name==app)
        result = db(query).select()
        if result: pltid = result[0]['plots']['id']

    p = plotmod.plot()

    # get the data for the pltid given
    try:
        result = db(plots.id==pltid).select()[0]
        plottype = result['ptype']
        options = result['options']
        datadef = result['datadef']
        #x = json.loads(datadef)
        title = result['title']
    except:
        redirect ('/plots/edit?app='+app+'&cid='+cid)

    # if plot not in DB return error
    if plottype is None:
        params = { 'cid': cid, 'app': app, 'user': u }
        params['err'] = "Sorry! This app does not support plotting capability"
        return template('error', params)

    # determine which view template to use
    if plottype == 'flot-bar': 
        tfn = 'plots/flot-bar'
    elif plottype == 'flot-cat': 
        tfn = 'plots/flot-cat'
    elif plottype == 'flot-line':
        tfn = 'plots/flot-line' 
    elif plottype == 'mpl-line' or plottype == 'mpl-bar':
        redirect('/mpl/'+pltid+'?app='+app+'&cid='+cid)
    else:
        tfn = 'plots/plot-line' 

    # get list of all plots for this app
    query = (apps.id==plots.appid) & (apps.name==app)
    list_of_plots = db(query).select()

    # extract data from files
    data = []
    ticks = []
    plotpath = ''
    result = db(datasource.pltid==pltid).select()

    for r in result:
        plotfn = r['filename']
        cols = r['cols']
        line_range = r['line_range']
        plotfn = re.sub(r"<cid>", c, plotfn)
        plotpath = sim_dir + plotfn
        (col1str,col2str) = cols.split(":")
        col1 = int(col1str); col2 = int(col2str)
        # do some postprocessing
        if line_range is not None:
            (line1str,line2str) = line_range.split(":")
            line1 = int(line1str); line2 = int(line2str)
            if myapps[app].postprocess > 0:
                dat = process.postprocess(plotpath,line1,line2)
            else:
                dat = p.get_data(plotpath,col1,col2,line1,line2) 
        else: 
            dat = p.get_data(plotpath,col1,col2)
        # clean data
        #dat = [d.replace('?', '0') for d in dat]
        data.append(dat)
        #data.append(p.get_data(plotpath,col1,col2))
        if plottype == 'flot-cat':
            ticks = p.get_ticks(plotpath,col1,col2)
    if not result:
        return template("error",err="need to specify at least one datasource")

    params = { 'cid': cid, 'pltid': pltid, 'data': data, 'app': app, 'user': u, 
               'ticks': ticks, 'title': title, 'plotpath': plotpath, 
               'rows': list_of_plots, 'options': options, 'datadef': datadef,
               'apps': myapps.keys() } 
    return template(tfn, params)

@get('/mpl/<pltid>')
def matplotlib(pltid):
    """Generate a random image using Matplotlib and display it"""
    # in the future create a private function __import__ to import third-party 
    # libraries, so that it can respond gracefully.  See for example the 
    # Examples section at https://docs.python.org/2/library/imp.html
    from pylab import savefig
    import numpy as np
    import StringIO
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    from matplotlib.figure import Figure
    global user
    app = request.query.app
    cid = request.query.cid

    fig = Figure()
    ax = fig.add_subplot(111)

    # get info about plot 
    p = plotmod.plot()
    result = db(plots.id==pltid).select()[0]
    plottype = result['ptype']
    options = result['options']
    title = result['title']

    # get info about data source
    # fix in the future to handle multiple data sources
    result = db(datasource.pltid==pltid).select()
    for r in result:
        plotfn = r['filename']
        cols = r['cols']
        line_range = r['line_range']
        (col1str,col2str) = cols.split(":")
        col1 = int(col1str)
        col2 = int(col2str)
        if line_range is not None:
            (line1str,line2str) = line_range.split(":")
            line1 = int(line1str)
            line2 = int(line2str)

    plotfn = re.sub(r"<cid>", cid, plotfn)
    sim_dir = myapps[app].user_dir+os.sep+user+os.sep+app+os.sep+cid+os.sep
    plotpath = sim_dir + plotfn
    xx = p.get_column_of_data(plotpath,col1)
    yy = p.get_column_of_data(plotpath,col2)
    #xx = np.asarray(p.get_column_of_data(sim_dir+plotfn,col1))
    #yy = np.asarray(p.get_column_of_data(sim_dir+plotfn,col2))
    #print 'xx:',type(xx), xx
    #print 'yy:',type(yy), yy

    # plot
    if plottype == 'mpl-line':
        ax.plot(xx, yy)
    elif plottype == 'mpl-bar':
        ax.hist(xx, yy, normed=1, histtype='bar', rwidth=0.8)
    else:
        return "ERROR: plottype not supported"
    canvas = FigureCanvas(fig)
    png_output = StringIO.StringIO()
    canvas.print_png(png_output)

    # save file
    if not os.path.exists(config.tmp_dir):
        os.makedirs(config.tmp_dir)
    fn = title+'.png'
    fig.set_size_inches(7,4)
    img_path = sim_dir + fn
    fig.savefig(img_path)
    #response.content_type = 'image/png'
    #return png_output.getvalue()

    # get list of all plots for this app
    query = (apps.id==plots.appid) & (apps.name==app)
    list_of_plots = db(query).select()

    params = {'image': fn, 'app': app, 'cid': cid, 'pltid': pltid, 'plotpath': plotpath, 
              'img_path': img_path, 'title': title, 'rows': list_of_plots, 'apps': myapps.keys() } 
    return template('plots/matplotlib', params)

@get('/monitor')
def monitor():
    global user
    cid = request.query.cid
    app = request.query.app
    params = { 'cid': cid, 'app': app, 'user': user, 'apps': myapps.keys() }
    return template('monitor', params)

@get('/zipcase')
def zipcase():
    """zip case on machine to prepare for download"""
    global user
    import zipfile
    app = request.query.app
    cid = request.query.cid
    base_dir = myapps[app].user_dir+os.sep+user+os.sep+app
    #zipkey = str(uuid.uuid4())
    #path = config.tmp_dir+os.sep+zipkey+".zip"
    path = base_dir+os.sep+cid+".zip"
    zf = zipfile.ZipFile(path, mode='w')
    sim_dir = base_dir+os.sep+cid
    for fn in os.listdir(sim_dir):
        zf.write(sim_dir+os.sep+fn)
    zf.close()
    #redirect("/jobs")
    #redirect(path) # download file directly
    #redirect("/aws?zipkey="+zipkey)
    redirect("/aws?status="+path)

@get('/zipget')
def zipget():
    """get zipfile from another machine, save to current machine"""
    zipkey = request.query.zipkey
    netloc = request.query.netloc
    #url = netloc + os.sep + config.tmp_dir + os.sep + zipkey + ".zip"
    url = netloc+os.sep+zipkey
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
    status = "file downloaded"
    redirect("/aws?status="+status)

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
        save_path_dir = appmod.apps_dir + os.sep + name
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

#def module_exists(module_name):
#    try:
#        __import__(module_name)
#    except ImportError:
#        return False
#    else:
#        return True

#@error(500)
#def error500(error):
#   return "Sorry, there was a 500 server error: " + str(error)

if __name__ == "__main__":
    load_apps()
    #list all dependencies
    #print sys.modules.keys()
    #default_app() # Google App Engine
    #run(app=app, host='0.0.0.0', port=8081, debug=True) # bottle
    run(server=config.server, app=app, host='0.0.0.0', port=8081, debug=True)
    #run(server='rocket', app=app, host='0.0.0.0', port=8081, debug=True)