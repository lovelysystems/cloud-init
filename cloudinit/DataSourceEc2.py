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

import DataSource

import cloudinit
import cloudinit.util as util
import socket
import urllib2
import time
import sys
import boto_utils
import os.path
import errno

class DataSourceEc2(DataSource.DataSource):
    api_ver  = '2009-04-04'
    cachedir = cloudinit.cachedir + '/ec2'

    def __init__(self):
        pass

    def __str__(self):
        return("DataSourceEc2")

    def get_data(self):
        seedret={ }
        if util.read_optional_seed(seedret,base=self.cachedir + "/"):
            self.userdata_raw = seedret['user-data']
            self.metadata = seedret['meta-data']
            cloudinit.log.debug("using seeded ec2 data in %s" % self.cachedir)
            return True

        try:
            if not self.wait_for_metadata_service():
                return False
            instance_userdata = boto_utils.get_instance_userdata(self.api_ver)
            self.userdata_raw = self._base64_detect_and_decode(instance_userdata)
            self.metadata = boto_utils.get_instance_metadata(self.api_ver)
            return True
        except Exception as e:
            print e
            return False

    def _base64_detect_and_decode(self, user_data):
        returned_data = None

        valid_headers=('#include',
                       '#!',
                       '#cloud-config',
                       '#upstart-job',
                       '#part-handler',
                       '#cloud-boothook',
                       'Content-Type: multipart/mixed'
                      )
        for header in valid_headers:
            if user_data.startswith(header):
                returned_data = user_data
                break
        if returned_data is None:
            import base64
            try:
                decoded_user_data = base64.urlsafe_b64decode(user_data)
                for header in valid_headers:
                    if decoded_user_data.startswith(header):
                        returned_data = decoded_user_data
                        break
            except Exception as e:
                cloudinit.log.error("Unable to decode base64 data: %s" % e)

        if returned_data is None:
            returned_data = user_data
        return returned_data

    def get_public_hostname(self):
        return (self.metadata['public-hostname'])

    def get_instance_id(self):
        return(self.metadata['instance-id'])

    def get_availability_zone(self):
        return(self.metadata['placement']['availability-zone'])

    def get_mirror_from_availability_zone(self, availability_zone = None):
        # availability is like 'us-west-1b' or 'eu-west-1a'
        if availability_zone == None:
            availability_zone = self.get_availability_zone()

        try:
            host="%s.ec2.archive.ubuntu.com" % availability_zone[:-1]
            socket.getaddrinfo(host, None, 0, socket.SOCK_STREAM)
            return 'http://%s/ubuntu/' % host
        except:
            return 'http://archive.ubuntu.com/ubuntu/'

    def wait_for_metadata_service(self, sleeps = 100):
        sleeptime = 1
        address = '169.254.169.254'
        starttime = time.time()

        url="http://%s/%s/meta-data/instance-id" % (address,self.api_ver)
        for x in range(sleeps):
            # given 100 sleeps, this ends up total sleep time of 1050 sec
            sleeptime=int(x/5)+1

            reason = ""
            try:
                req = urllib2.Request(url)
                resp = urllib2.urlopen(req, timeout=2)
                if resp.read() != "": return True
                reason = "empty data [%s]" % resp.getcode()
            except urllib2.HTTPError, e:
                reason = "http error [%s]" % e.code
            except urllib2.URLError, e:
                reason = "url error [%s]" % e.reason

            if x == 0:
                cloudinit.log.warning("waiting for metadata service at %s\n" % url)

            cloudinit.log.warning("  %s [%02s/%s]: %s\n" %
                (time.strftime("%H:%M:%S"), x+1, sleeps, reason))
            time.sleep(sleeptime)

        cloudinit.log.critical("giving up on md after %i seconds\n" %
                  int(time.time()-starttime))
        return False

    def device_name_to_device(self, name):
        # consult metadata service, that has
        #  ephemeral0: sdb
        # and return 'sdb' for input 'ephemeral0'
        if not self.metadata.has_key('block-device-mapping'):
            return(None)

        found = None
        for entname, device in self.metadata['block-device-mapping'].items():
            if entname == name:
                found = device
                break
            # LP: #513842 mapping in Euca has 'ephemeral' not 'ephemeral0'
            if entname == "ephemeral" and name == "ephemeral0":
                found = device
        if found == None:
            cloudinit.log.warn("%s does not seem to be configured on this system" % name)
            return None

        # LP: #611137
        # the metadata service may believe that devices are named 'sda'
        # when the kernel named them 'vda' or 'xvda'
        # we want to return the correct value for what will actually
        # exist in this instance
        mappings = { "sd": ("vd", "xvd") }
        ofound = found
        short = os.path.basename(found)

        if not found.startswith("/"):
            found="/dev/%s" % found

        if os.path.exists(found):
            return(found)

        for nfrom, tlist in mappings.items():
            if not short.startswith(nfrom): continue
            for nto in tlist:
                cand = "/dev/%s%s" % (nto, short[len(nfrom):])
                if os.path.exists(cand):
                    cloudinit.log.debug("remapped device name %s => %s" % (found,cand))
                    return(cand)
        return ofound
