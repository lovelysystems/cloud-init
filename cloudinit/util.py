# vi: ts=4 expandtab
#
#    Copyright (C) 2009-2010 Canonical Ltd.
#
#    Author: Scott Moser <scott.moser@canonical.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License version 3, as
#    published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
import yaml
import os
import errno
import subprocess
from Cheetah.Template import Template
import cloudinit
import urllib2
import logging
import traceback

WARN = logging.WARN
DEBUG = logging.DEBUG
INFO = logging.INFO

# for upgrade levels
UPGRADE_NONE     = 0
UPGRADE_SECURITY = 1
UPGRADE_BUGFIX   = 2
UPGRADE_ALL      = 3

def read_conf(fname):
    try:
            stream = open(fname,"r")
            conf = yaml.load(stream)
            stream.close()
            return conf
    except IOError as e:
        if e.errno == errno.ENOENT:
            return { }
        raise

def get_base_cfg(cfgfile,cfg_builtin=""):
    syscfg = read_conf(cfgfile)
    if cfg_builtin:
        builtin = yaml.load(cfg_builtin)
    else:
        return(syscfg)
    return(mergedict(syscfg,builtin))

def get_cfg_option_bool(yobj, key, default=False):
    if not yobj.has_key(key): return default
    val = yobj[key]
    if val is True: return True
    if str(val).lower() in [ 'true', '1', 'on', 'yes']:
        return True
    return False

def get_cfg_option_str(yobj, key, default=None):
    if not yobj.has_key(key): return default
    return yobj[key]

def get_cfg_option_list_or_str(yobj, key, default=None):
    if not yobj.has_key(key): return default
    if isinstance(yobj[key],list): return yobj[key]
    return([yobj[key]])

# merge values from src into cand.
# if src has a key, cand will not override
def mergedict(src,cand):
    if isinstance(src,dict) and isinstance(cand,dict):
        for k,v in cand.iteritems():
            if k not in src:
                src[k] = v
            else:
                src[k] = mergedict(src[k],v)
    return src

def write_file(file,content,mode=0644,omode="wb"):
        try:
            os.makedirs(os.path.dirname(file))
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise e

        f=open(file,omode)
        if mode != None:
            os.chmod(file,mode)
        f.write(content)
        f.close()

# get keyid from keyserver
def getkeybyid(keyid,keyserver):
   shcmd="""
   k=${1} ks=${2};
   exec 2>/dev/null
   [ -n "$k" ] || exit 1;
   armour=$(gpg --list-keys --armour "${k}")
   if [ -z "${armour}" ]; then
      gpg --keyserver ${ks} --recv $k >/dev/null &&
         armour=$(gpg --export --armour "${k}") &&
         gpg --batch --yes --delete-keys "${k}"
   fi
   [ -n "${armour}" ] && echo "${armour}"
   """
   args=['sh', '-c', shcmd, "export-gpg-keyid", keyid, keyserver]
   return(subp(args)[0])

def subp(args, input=None):
    s_in = None
    if input is not None:
        s_in = subprocess.PIPE
    sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=s_in)
    out,err = sp.communicate(input)
    if sp.returncode is not 0:
        raise subprocess.CalledProcessError(sp.returncode,args)
    return(out,err)

templatesdir = '/etc/cloud/templates'

def render_to_file(template, outfile, searchList):
    t = Template(file=os.path.join(templatesdir, '%s.tmpl' % template),
                 searchList=[searchList])
    f = open(outfile, 'w')
    f.write(t.respond())
    f.close()

# read_optional_seed
# returns boolean indicating success or failure (presense of files)
# if files are present, populates 'fill' dictionary with 'user-data' and
# 'meta-data' entries
def read_optional_seed(fill,base="",ext="", timeout=2):
    try:
        (md,ud) = read_seeded(base,ext,timeout)
        fill['user-data']= ud
        fill['meta-data']= md
        return True
    except OSError, e:
        if e.errno == errno.ENOENT:
            return False
        raise
    

# raise OSError with enoent if not found
def read_seeded(base="", ext="", timeout=2):
    if base.startswith("/"):
        base="file://%s" % base

    if base.find("%s") >= 0:
        ud_url = base % ("user-data" + ext)
        md_url = base % ("meta-data" + ext)
    else:
        ud_url = "%s%s%s" % (base, "user-data", ext)
        md_url = "%s%s%s" % (base, "meta-data", ext)

    try:
        md_resp = urllib2.urlopen(urllib2.Request(md_url), timeout=timeout)
        ud_resp = urllib2.urlopen(urllib2.Request(ud_url), timeout=timeout)

        md_str = md_resp.read()
        ud = ud_resp.read()
        md = yaml.load(md_str)

        return(md,ud)
    except urllib2.HTTPError:
        raise
    except urllib2.URLError, e:
        if isinstance(e.reason,OSError) and e.reason.errno == errno.ENOENT:
           raise e.reason 
        raise e

def logexc(log,lvl=logging.DEBUG):
    log.log(lvl,traceback.format_exc())
