"""
Just holds world_objects and can serialise/deserialise state. No rendering.
"""

import logging
llog = logging.getLogger(__name__) # the name 'log' is taken in sdl2

import math
import copy

import vector
import world_objects


class World:
    def __init__(self, serialized_world_jsn, conf):
        self.conf = conf
        self.nodes = []
        self.links = []
        self.nodes_dict = {} # integers. 16-bit node addresses
        self.links_dict = {} # a pair of node objects. (node1, node2) is equivalent to (node2, node1), but only one pair exists in links_dict

        # saved when closing the windows. loaded at startup.
        self.session_node_positions = {} # {"0x31FE": (x,y), ..}

#        self.deserialize_world(serialized_world_jsn)

    def serialize_node(self, node):
        return {
            "node_id": node.node_id,
            "node_idstr": node.node_idstr,
            "name": node.node_name,
            "color": node.node_color,
            "attrs": copy.deepcopy(node.attrs),
        }

    # def serialize_link(self, link):
    #     return {
    #         "node1_id": link.node1.node_id,
    #         "node1_idstr": link.node1.node_idstr,
    #         "node2_id": link.node2.node_id,
    #         "node2_idstr": link.node2.node_idstr,
    #         "name": node.node_name,
    #         "color": node.node_color,
    #         "attrs": node.attrs,
    #     }

    def serialize_world(self):
        """
        world is a list of nodes and a list of links.
        """
        nodes = [] # a list of node dictionaries
        for node in self.nodes:
            nodes.append( self.serialize_node(node) )

        # links = [] # a list of link dictionaries
        # for link in self.links:
        #     links.append( self.serialize_link(link) )

        # world = {"nodes": nodes, "links": links}
        world = {"nodes": nodes}
        return world
        #txt = json.dumps(world, indent=4) #, sort_keys=True
        #return txt

    def deserialize_node(self, dct):
        #import pprint
        #llog.info(pprint.pformat(dct))
        pos = self.get_node_session_pos( dct["node_id"] )
        node = world_objects.Node( vector.Vector(pos), dct["node_id"], dct["color"] )
        node.node_idstr = dct["node_idstr"]
        node.node_name = dct["name"]
        node.attrs = copy.deepcopy(dct["attrs"])
        return node

    def deserialize_world(self, dct):
        #import pprint
        #llog.info("\n\n\nRESTORING")
        #llog.info(pprint.pformat(dct))

        self.links = []
        self.nodes = []
        self.links_dict = {}
        self.nodes_dict = {}
        sernodes = dct.get("nodes")
        if sernodes:
            for node_dict in sernodes:
                node = self.deserialize_node(node_dict)
                self.nodes.append(node)
                self.nodes_dict[node.node_id] = node

    def get_link(self, src_node, dst_node):
        """ create a new link object if not found from self.links.
        fill self.links and self.links_dict (the dict both with src_node_id and dst_node_id) """
        if (src_node, dst_node) in self.links_dict:
            return self.links_dict[(src_node, dst_node)]
        elif (dst_node, src_node) in self.links_dict:
            return self.links_dict[(dst_node, src_node)]
        else:
            link = world_objects.Link(src_node, dst_node)
            self.links.append(link)
            self.links_dict[(src_node, dst_node)] = link
            return link

    def get_node_color(self, origin_node_id):
        """ try to return a different color for different nodes. just some hardcoded values. """
        origin_node_id %= 11
        if origin_node_id == 9:
            return 0.753, 0.753, 0.753, 1.
        if origin_node_id == 8:
            return 0.824, 0.412, 0.118, 1.
        if origin_node_id == 7:
            return 1.000, 0.000, 1.000, 1.
        if origin_node_id == 6:
            return 1.000, 1.000, 0.000, 1.
        if origin_node_id == 5:
            return 1.000, 0.627, 0.478, 1.
        if origin_node_id == 4:
            return 0.498, 1.000, 0.000, 1.
        if origin_node_id == 3:
            return 0.000, 1.000, 1.000, 1.
        if origin_node_id == 2:
            return 1.000, 0.922, 0.804, 1.
        if origin_node_id == 1:
            return 0.871, 0.722, 0.529, 1.
        if origin_node_id == 0:
            return 0.000, 0.749, 1.000, 1.
        if origin_node_id == 0:
            return 0.500, 0.549, 1.000, 1.

        return 0.8, 0.8, 0.8, 1.0

    def get_create_node(self, node_id):
        if node_id in self.nodes_dict:
            return self.nodes_dict[node_id]
        else:
            pos = self.get_node_session_pos(node_id)
            node = world_objects.Node( vector.Vector(pos), node_id, self.get_node_color(node_id) )
            self.nodes.append(node)
            self.nodes_dict[node.node_id] = node
            return node

    def get_create_named_node(self, node_id_name):
        """ Createa node if it doesn't exist yet. Also set its name if given.
        node_id_name can be "12AB_somename" or "12AB" """
        n = node_id_name.split("_", 1)
        node_id = int(n[0], 16)
        if node_id in self.nodes_dict:
            node = self.nodes_dict[node_id]
        else:
            node = self.get_create_node(node_id)

        if len(n) == 2 and node.node_name != n[1]:
            node.node_name = n[1]

        return node

    def get_node_session_pos(self, node_id):
        if node_id not in self.session_node_positions:
            h = 0.
            r = 1. + 0.5 * len(self.nodes)
            a = float(len(self.nodes)) / (r + 10) * 15.
            x, y = r * math.sin(a), r * math.cos(a)
            return (x, h, y)
        else:
            return self.session_node_positions[node_id]

    def tick(self, dt):
        for link in self.links:
            link.tick(dt)
        for node in self.nodes:
            node.tick(dt)

    # def save_graph_file(self, filename="sensormap.txt"):
    #     d = {"format": "sensed node graph", "format_version": "2013-12-19", "nodes": [], "edges": []}

    #     for node in self.nodes:
    #         p = node.pos
    #         n = {"id": node.node_id, "pos": [p[0], p[1], p[2]]}
    #         d["nodes"].append(n)

    #     edge_count = 0
    #     for node1 in self.nodes:
    #         for node2 in self.nodes:
    #             if node1 != node2:
    #                 edge_count += 1
    #                 e = {"id": edge_count, "source": node1.node_id, "dest": node2.node_id, "link_quality": self._calc_link_quality(node1, node2)}
    #                 d["edges"].append(e)

    #     txt = json.dumps(d, indent=4, sort_keys=True)

    #     with open(filename, "wb") as f:
    #         f.write(txt)

    def close(self):
        pass
