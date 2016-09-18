def slurp_file(path):
    """read file given by path and return the contents of the file
       as a single string datatype"""
    try:
        with open(path,'r') as f:
            data = f.read()
        return data
    except IOError:
        return("ERROR: the file cannot be opened or does not exist " + path)

# thanks to http://stackoverflow.com/a/1094933/2636544
def sizeof_fmt(num, suffix='B'):
    for unit in ['','K','M','G','T','P','E','Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Yi', suffix)