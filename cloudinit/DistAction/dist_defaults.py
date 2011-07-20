# vi: ts=4 expandtab
#
#    Copyright (C) 2009-2010 Canonical Ltd.
#
#    Author: Scott Moser <scott.moser@canonical.com>
#
#    Modifications Copyright (C) 2010 Amazon.com, Inc. or its affiliates.
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
#

#    Modifications:  New file that pulls functionality from cloud-init.py
#                    to support generic default actions instead of
#                    Ubuntu-specific ones.
#
#                    This file can be used to support any actions that are
#                    not defined by a separate module (configurable in
#                    dist-defs.cfg).  One can override the actions in this
#                    handler by specifying a different common handler.
import sys
import cloudinit
import subprocess
import cloudinit.util as util

# (common.set_hostname)
def set_defaults(locale):
    cloudinit.log.debug("-- defaults handler/set_defaults() --")
    locale_file = ""

    try:
        subprocess.Popen(['locale-gen', locale]).communicate()
        subprocess.Popen(['update-locale', locale]).communicate()
        locale_file = "/etc/default/locale"
    except OSError as e:
        locale_file = "/etc/sysconfig/i18n"

    if locale_file != "":
        util.render_to_file('default-locale', locale_file, \
                            { 'locale' : locale })

# (common.set_hostname)
def set_hostname(hostname):
    cloudinit.log.debug("-- defaults handler/set_hostname() --")

    subprocess.Popen(['hostname', hostname]).communicate()
    f=open("/etc/hostname","wb")
    f.write("%s\n" % hostname)
    f.close()

# (init.notify)
def notify(name, value):
    cloudinit.log.debug("-- defaults handler/notify() --")

    # This should work in distributions with upstart:
    try:
        subprocess.Popen(['initctl', 'emit', 'cloud-config',
                          '%s=%s' % (name,value)]).communicate()
    except:
        # No harm done (distribution doesn't support upstart)
        pass

def update():
    raise NotImplementedError("Update needs to be defined in dist_repo_[name]")

def upgrade(upgrade=util.UPGRADE_NONE):
    raise NotImplementedError("Upgrade needs to be defined in dist_repo_[name]")

def install(pkglist):
    raise NotImplementedError("Install needs to be defined in dist_repo_[name]")

def add(repolist):
    raise NotImplementedError("Add needs to be defined in dist_repo_[name]")

def generate(mirror):
    raise NotImplementedError("Generate needs to be defined in dist_repo_[name]")

