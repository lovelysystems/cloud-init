#!/usr/bin/python2.6
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

import sys
import cloudinit
import cloudinit.CloudConfig
import logging
import os
import traceback

def Usage(out = sys.stdout):
    out.write("Usage: %s name\n" % sys.argv[0])
    
def main():
    # expect to be called with
    #   name [ freq [ args ]
    #   run the cloud-config job 'name' at with given args
    # or
    #   read cloud config jobs from config (builtin -> system)
    #   and run all in order

    if len(sys.argv) < 2:
        Usage(sys.stderr)
        sys.exit(1)
    if sys.argv[1] == "all":
        name = "all"
    else:
        freq = None
        run_args = []
        name=sys.argv[1]
        if len(sys.argv) > 2:
            freq = sys.argv[2]
            if freq == "None":
                freq = None
        if len(sys.argv) > 3:
            run_args=sys.argv[3:]

    cloudinit.logging_set_from_cfg_file()
    log = logging.getLogger()
    log.info("cloud-init-cfg %s" % sys.argv[1:])

    cfg_path = cloudinit.cloud_config
    cfg_env_name = cloudinit.cfg_env_name
    if os.environ.has_key(cfg_env_name):
        cfg_path = os.environ[cfg_env_name]

    cc = cloudinit.CloudConfig.CloudConfig(cfg_path)

    module_list = [ ]
    if name == "all":
        # create 'module_list', an array of arrays
        # where array[0] = config
        #       array[1] = freq
        #       array[2:] = arguemnts
        if "cloud_config_modules" in cc.cfg:
            for item in cc.cfg["cloud_config_modules"]:
                if isinstance(item,str):
                    module_list.append((item,))
                elif isinstance(item,list):
                    module_list.append(item)
                else:
                    fail("Failed to parse cloud_config_modules",log)
        else:
            fail("No cloud_config_modules found in config",log)
    else:
        module_list.append( [ name, freq ] + run_args )

    failures = []
    for cfg_mod in module_list:
        name = cfg_mod[0]
        freq = None
        run_args = [ ]
        if len(cfg_mod) > 1:
            freq = cfg_mod[1]
        if len(cfg_mod) > 2:
            run_args = cfg_mod[2:]

        try:
            log.debug("handling %s with freq=%s and args=%s" %
                (name, freq, run_args ))
            cc.handle(name, run_args, freq=freq)
        except:
            log.warn(traceback.format_exc())
            err("config handling of %s, %s, %s failed\n" %
                (name,freq,run_args), log)
            failures.append(name)
            
    sys.exit(len(failures))

def err(msg,log=None):
    if log:
        log.error(msg)
    sys.stderr.write(msg + "\n")

def fail(msg,log=None):
    err(msg,log)
    sys.exit(1)

if __name__ == '__main__':
    main()
