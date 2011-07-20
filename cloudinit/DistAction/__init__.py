#    Copyright 2010 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the GNU Public License, Version 3 (the "License").
#    You may not use this file except in compliance with the License. A copy
#    of the License is located at
#
#    http://www.opensource.org/licenses/gpl-3.0.html
#
#    or in the "COPYING" file accompanying this file.
#
#    This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES
#    OR CONDITIONS OF ANY KIND, either express or implied. See the License
#    for the specific language governing permissions and limitations under
#    the License.


#
#    This module provides a distribution-agnostic interface to administrative
#    actions that can be called by cloud-init handlers.  Distribution maintainers
#    should write new handlers as necessary and declare what handlers to use for
#    various actions using dist-defs.cfg.  This appeared to be the cleanest
#    approach to portability because distribution detection is hard to get right
#    and is error-prone.
import yaml
import cloudinit
import cloudinit.util as util
import sys
import traceback
import socket
import subprocess

class DistAction:
    cfgfile = None
    cfg = None

    def __init__(self,cfgfile):
        self.cloud = cloudinit.CloudInit()

        self.cfg = util.read_conf(cfgfile)
        self.cloud.get_data_source()

        self.prepare_handlers()

    def get_config_option(self, option):
        value = None

        try:
            value = self.cfg[option]
        except KeyError as e:
            pass

        return value

    def prepare_handlers(self):
        self.handlers = {}

        handlers_cfg = self.get_config_option('distribution-handlers')

        # Allows user to add handlers via config file
        for key, value in handlers_cfg.items():
            handler_name = "dist_%s_%s" % (key, value.replace("-","_"))
            cloudinit.log.debug("Loading %s" % handler_name)
            try:
                handler = __import__(handler_name, globals())
            except:
                cloudinit.log.warn("Failed to load %s!" % handler_name)
                continue
            self.handlers[key] = handler

        # Initialize defaults for required options:
        handlers_required = [ 'init', 'repo', 'common' ]
        default_handler = None

        for key in handlers_required:
            if key in self.handlers:
                # Already defined a handler in config
                continue
            else:
                # Assign the default handler
                if not default_handler:
                    try:
                        default_handler = __import__("dist_defaults", globals())
                    except:
                        cloudinit.log.error("Failed to load default handler")
                        raise

                self.handlers[key] = default_handler

    def __getattr__(self, lookup):
        # repo_upgrade -> repo.upgrade (better way to do this?)
        (handler, func) = lookup.split('_',1)

        dispatch_func = None

        try:
            dispatch_func = getattr(self.handlers[handler], func)
        except AttributeError:
            cloudinit.log.error("Could not find handler for %s" % lookup)
            #raise ?

        return dispatch_func

    def get_config_section(self,section=None):
        if section is None:
            return self.cfg

        elif section in self.cfg:
            return self.cfg[section]

        else:
            return {}


