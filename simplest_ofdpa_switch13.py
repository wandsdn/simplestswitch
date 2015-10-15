# Copyright (C) 2013 Nippon Telegraph and Telephone Corporation.
# Copyright (C) 2015 Brad Cowie
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
A very basic OpenFlow 1.3 2 port switch for broadcom's of-dpa pipeline
"""

import logging, traceback

from ryu.base import app_manager
from ryu.controller import ofp_event, dpset
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3


class SimplestSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    ACL_TABLE = 60

    def __init__(self, *args, **kwargs):
        super(SimplestSwitch13, self).__init__(*args, **kwargs)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        try:
            datapath = ev.msg.datapath
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser

            logging.info("Configuring new datapath 0x%x" % datapath.id)

            # clean up all groups and flows
            self.del_flows(datapath)
            self.del_groups(datapath)

            # install table-miss flow entry
            match = parser.OFPMatch()
            actions = []
            self.add_flow(datapath, 0, match, actions)

            # add group for output ports, of-dpa does not support output
            # directly instead special groups must be used which map to
            # output ports
            ports = [1, 2]
            for port in ports:
                bkt = [parser.OFPBucket(actions=[parser.OFPActionOutput(port)])]
                self.add_group(datapath, bkt, self.l2_unfiltered_if_group(port),
                    ofproto.OFPGT_INDIRECT)

            # IN PORT 1, OUTPUT PORT 2
            match = parser.OFPMatch(in_port=1)
            actions = [parser.OFPActionGroup(self.l2_unfiltered_if_group(2))]
            self.add_flow(datapath, 1000, match, actions)


            # IN PORT 2, OUTPUT PORT 1
            match = parser.OFPMatch(in_port=2)
            actions = [parser.OFPActionGroup(self.l2_unfiltered_if_group(1))]
            self.add_flow(datapath, 1000, match, actions)
        except:
            traceback.print_exc()

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    table_id=self.ACL_TABLE,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst,
                                    table_id=self.ACL_TABLE)
        datapath.send_msg(mod)

    def add_group(self, datapath, buckets, group_id, group_type):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        msg = parser.OFPGroupMod(datapath, ofproto.OFPFC_ADD, group_type,
                group_id, buckets)
        datapath.send_msg(msg)

    def del_groups(self, datapath):
        """ Deletes all existing groups """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        msg = parser.OFPGroupMod(datapath, ofproto.OFPGC_DELETE, 0,
                ofproto.OFPG_ALL)
        datapath.send_msg(msg)

    def del_flows(self, datapath):
        """ Deletes all existing flows """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        msg = parser.OFPFlowMod(datapath=datapath, table_id=ofproto.OFPTT_ALL,
                command=ofproto.OFPFC_DELETE, out_port=ofproto.OFPP_ANY,
                out_group=ofproto.OFPG_ANY)
        datapath.send_msg(msg)


    def l2_unfiltered_if_group(self, port):
	""" An indirect OpenFlow interface with no VLAN filtering or tagging

        This can be used to output packets out a specific port
        id=[0:15] Port id --- [27:16] Reserved (0) --- [28:31] Type (11)
        """
	MAX_PORT = 0xFFFF
        assert(port <= MAX_PORT)
        return self._ofdpa_group_id(port, 11)

    def _ofdpa_group_id(self, index, type):
        """ OFDPA group id builder """
        TYPE_OFFSET = 28
        INDEX_OFFSET = 0
        MAX_TYPE = 12
        MAX_INDEX = 0xFFFFFFF
        assert(type <= MAX_TYPE)
        assert(index <= MAX_INDEX)
        return index | (type<<TYPE_OFFSET)

