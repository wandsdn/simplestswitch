# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
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
A very basic OpenFlow 1.0 2 port switch for testing OF implementations
"""

import logging

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0


class SimplestSwitch10(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimplestSwitch10, self).__init__(*args, **kwargs)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        logging.info("Configuring new datapath 0x%x" % datapath.id)

        # install table-miss flow entry
        match = parser.OFPMatch()
        actions = []
        self.add_flow(datapath, 0, match, actions)

        # IN PORT 1, OUTPUT PORT 2
        match = parser.OFPMatch(in_port=1)
        actions = [parser.OFPActionOutput(2)]
        self.add_flow(datapath, 1000, match, actions)

        # IN PORT 2, OUTPUT PORT 1
        match = parser.OFPMatch(in_port=2)
        actions = [parser.OFPActionOutput(1)]
        self.add_flow(datapath, 1000, match, actions)

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto

        mod = datapath.ofproto_parser.OFPFlowMod(
            datapath=datapath, match=match, cookie=0,
            command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
            priority=priority,
            flags=ofproto.OFPFF_SEND_FLOW_REM, actions=actions)
        datapath.send_msg(mod)
