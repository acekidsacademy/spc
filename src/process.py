#!/usr/bin/python
import os
from bottle import template

def preprocess(params,fn,base_dir=""):
    """in the future these need to be generalized or hooked in"""
    buf = ''
    if fn == 'fpg.in':  
        # convert input key/value params to command-line style args
        if 'cid' in params: del params['cid']        
        for key, value in (params.iteritems()):
            if key == 't_pseudo_data':
                if value=='true': value = ''
                else: continue # don't output anything when this param is false
            option = '-' + key.split('_')[0] # extract first letter
            buf += option + value + ' ' 
        sim_dir = os.path.join(base_dir, fn)
        return _write_file(buf, sim_dir)
    elif fn == 'Nemo2.ini':
        for key, value in (params.iteritems()):
            buf += key + ' ' + value + '\n'
        sim_dir = os.path.join(base_dir, fn)
        return _write_file(buf, sim_dir)
    elif fn == 'simple.sim':
        # use a template based approach 
        buf = template('simple.sim', params) 
        sim_dir = os.path.join(base_dir, fn)
        return _write_file(buf, sim_dir)
    elif fn == 'terra.in':
        # this doesn't work because already redirecting output to terra.out
        # only way it might work is if we don't redirect output to terra.out
        src = os.path.join(base_dir, "out"+params['casenum']+".00")
        dst = os.path.join(base_dir, "terra.out")
        #os.symlink(src, dst)
    elif fn == 'pbs.script':
        buf  = "#!/bin/sh\n"
        buf += "cd $PBS_O_WORKDIR"
        buf += "/usr/local/bin/mpirun -np 2 ./mendel"
        return buf

def _write_file(data, path):
    try:
        open(path,'w').write(data)
        return True
    except IOError:
        return "IOError:", IOError

def postprocess(path,line1,line2):
    """return data as an array...
    turn data that looks like this:
        100       0.98299944  200       1.00444448      300       0.95629907      
    into something that looks like this:
        [[100, 0.98299944], [200, 1.00444448], [300, 0.95629907], ... ]"""
    y = []
    data = open(path, 'rU').readlines()
    subdata = data[line1:line2]
    xx = []; yy = []
    for d in subdata: 
        xy = d.split()
        for (j,x) in enumerate(xy):
            if j%2: yy += [x]
            else:   xx += [x]
    data = [] 
    z = zip(xx,yy)
    for (x,y) in z:
        a = [ int(x), float(y) ]
        data += [ a ]
    return data

