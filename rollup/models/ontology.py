__author__ = 'Aaron J Masino'

import networkx as nx
from rollup.utils import collections
from math import log, sqrt

class Ontotology:
    """Ontology class for ontology represented as a DAG with only IS_A relationships"""
    def __init__(self, netx_concept_graph,
                 annotated_objects_key = 'object_list',
                 is_direct_annotator_key = 'is_direct_annotator'):
        self.graph = netx_concept_graph
        self.annotated_objects_key = annotated_objects_key
        self.is_direct_annotator_key = is_direct_annotator_key

    def leaf_nodes(self):
        """Returns all nodes that have at least 1 parent concept and no child concepts"""
        return [n for n in self.graph.nodes() if self.graph.out_degree(n) != 0 and self.graph.in_degree(n) == 0]

    def root_nodes(self):
        """Returns all nodes that have no parent concepts as a list."""
        return [n for n in self.graph.nodes() if self.graph.out_degree(n) == 0]

    def total_annotated_objects(self):
        """annotated_objects_key: key associated with node attribute that contains the list of objects annotated by the node
        either directly or indirectly through true path rule inheritance

        returns: total number of unique object annotated by at least one concept"""
        l = []
        for rid in self.root_nodes():
            rn = self.graph.node[rid]
            l = collections.merge_lists(l, rn[self.annotated_objects_key])
        return len(l)

    def annotators(self):
        """
        is_direct_annotator_key: key associated with node attribute that indicates if the ontology concept represented
        by the node directly annotates any object

        returns: list of concepts that directly annotate an object as indicated by is_visit_annotator attribute
                [this does NOT include annotations inherited through descendants]
        """
        l = []
        for (p, d) in self.graph.nodes(data=True):
            if d[self.is_direct_annotator_key]:
                l.append(p)
        return l

    def total_annotators(self):
        """
        is_direct_annotator_key: key associated with node attribute that indicates if the ontology concept represented by
        the node directly annotates any object [this does NOT include annotations inherited through descendants]

        returns: number of concepts that directly annotate an object as indicated by annotator_attribute_key
        """
        return len(self.annotators())

    def descendant_concepts(self, concept_id):
        """wrapper method to avoid confusion due to design of is_a relationship which
        runs in opposite direction from ancestor relation direction used in networkX"""
        return nx.ancestors(self.graph, concept_id)

    def parent_concepts(self, concept_id):
        """wrapper method to avoid confusion due to design of is_a relationship which
        runs in opposite direction from ancestor relation direction used in networkX"""
        parent_nodes = self.graph[concept_id]
        return list(parent_nodes.keys())

    def information_content(self, concept_id, N):
        """

        :param concept_id: id of ontology concept
        :param N: total number of annotated objects
        :param annotated_objects_key: key associated with node attribute that contains the list of objects annotated
               by the node either directly or indirectly through true path rule inheritance
        :return: information content for the concept
        """
        n = len(self.graph.node[concept_id][self.annotated_objects_key])
        if n == 0:
            # this node and its descendants do does not annotate anything
            return float("inf")
        else:
            return log(N / float(n))

    def total_information_content(self, N,
                                  direct_annotators_only=False):
        """

        :param N: total number of annotated objects
        :param annotated_objects_key: key associated with node attribute that contains the list of objects annotated
               by the node either directly or indirectly through true path rule inheritance
        :param is_direct_annotator_key: key associated with node attribute that indicates if the ontology concept represented by
        the node directly annotates any object [this does NOT include annotations inherited through descendants]
        :param direct_annotators_only: if True only count information content for direct annotators
        :return: sum of information content of all concepts
        """
        tic = 0
        for node in self.graph.nodes:
            if (direct_annotators_only and self.graph.node[node][self.is_direct_annotator_key]) or not direct_annotators_only:
                tic += self.information_content(node, N)
        return tic

    def annotators_information_content(self, N):
        """

        :param N: total number of annotated objects
        :param annotated_objects_key: annotated_objects_key: key associated with node attribute that contains the list of objects annotated
               by the node either directly or indirectly through true path rule inheritance
        :param is_direct_annotator_key: is_direct_annotator_key: key associated with node attribute that indicates if the ontology concept represented by
        the node directly annotates any object [this does NOT include annotations inherited through descendants]
        :return: dictionary {concept_id : information content} for all concepts that directly annotate an object
        """
        ic_dict = {}
        for a in self.annotators():
            ic_dict[a] = self.information_content(a, N)
        return ic_dict

    def mean_annotations_per_concept(self, direct_annotators_only = True):
        s = 0
        d = 0
        if direct_annotators_only:
            for cid in self.annotators():
                d += 1
                s += len(self.graph.node[cid][self.annotated_objects_key])
        else:
            for cid in self.graph.nodes():
                d += 1
                s += len(self.graph.node[cid][self.annotated_objects_key])
        return s / float(d)

    def stdev_annotations_per_concept(self, direct_annotators_only = True, ddof = 0):
        """

        :param direct_annotators_only:
        :param ddof: denominator for stdev calculation is N - ddof. If you're interpretation is
        that the collection of concepts is the entire population, ddof = 0.
        :return:
        """
        m = self.mean_annotations_per_concept(direct_annotators_only)
        s = 0
        d = 0
        if direct_annotators_only:
            for cid in self.annotators():
                d += 1
                s += (len(self.graph.node[cid][self.annotated_objects_key])-m)**2
        else:
            for cid in self.graph.nodes():
                d += 1
                s += (len(self.graph.node[cid][self.annotated_objects_key])-m)**2
        return sqrt(s / float(d-ddof))

    def serialize_nodes(self, file_path):
        first_line = True
        with open(file_path, 'a+') as f:
            for node in self.graph.nodes():
                parents = self.parent_concepts(node)
                line = "{0}".format(node)
                if parents:
                    line = "{0}:{1}".format(line, parents[0])
                if len(parents) > 1:
                    for p in parents[1:]:
                        line = "{0},{1}".format(line, p)
                if first_line:
                    first_line = False
                else:
                    line = "\n{0}".format(line)
                f.write(line)


class OntologyFactory:
    _shared_state = {}
    children_key = '___children___'
    complete_object_list_key = '___complete_object_list___'

    def __init__(self):
        self.__dict__ = self._shared_state

    def build_ontology_from_files(self, ontology_filename,
                                  annotations_filename,
                                  annotated_objects_key='object_list',
                                  is_direct_annotator_key='is_direct_annotator'
                                  ):
        graph = nx.DiGraph()
        edge_dict = {}

        # read in ontology file and add nodes and edges
        print("Adding nodes to ontology ...")
        with open(ontology_filename, 'r') as f:
            for line in f.readlines():
                data = line.split(":")
                cid = data[0].strip()
                if len(data)>1:
                    edge_dict[cid] = [x.strip() for x in data[1].split(",")]
                graph.add_node(cid)
                n = graph.node[cid]
                n[annotated_objects_key] = []
                n[is_direct_annotator_key] = False
                n[self.children_key] = []
                n[self.complete_object_list_key] = False

        print("Adding IS_A concept relations ...")
        for child, parent_list in edge_dict.items():
            for parent in parent_list:
                graph.add_edge(child, parent, relation="IS_A")
                graph.node[parent][self.children_key].append(child)

        # read in annotation files and update annotated object list and is object annotator attributes
        print("Building concept annotation lists ...")
        with open(annotations_filename, 'r') as f:
            for line in f.readlines():
                data = line.split(":")
                cid = data[0].strip()
                if len(data)>1:
                    objects = [x.strip() for x in data[1].split(",")]
                    n = graph.node[cid]
                    n[annotated_objects_key] = objects
                    n[is_direct_annotator_key] = True

        # update all non-leaves with annotated objects inherited from descendants
        ## set leaf nodes as completed
        for node in graph.node():
            if graph.out_degree(n) != 0 and graph.in_degree(n) == 0:
                node[self.complete_object_list_key] = True

        ## update the non-leaf nodes
        # for computational efficiency this needs to start at the leaves and work up through ancestors of each leaf
        # adding the leaf visits to the ancestors
        nodes_to_update = []
        for n in graph.nodes():
            if not graph.node[n][self.complete_object_list_key]:
                nodes_to_update.append(n)
        nodes_to_update = set(nodes_to_update)
        while nodes_to_update:
            for p in nodes_to_update:
                update_p = True
                pn = graph.node[p]
                p_children = pn[self.children_key]
                for c in p_children:
                    update_p = update_p and graph.node[c][self.complete_object_list_key]
                if update_p:
                    obj_list = pn[annotated_objects_key]
                    for c in p_children:
                        c_obj_list = graph.node[c][annotated_objects_key]
                        obj_list = collections.merge_lists(obj_list, c_obj_list)
                    pn[annotated_objects_key] = obj_list
                    pn[self.complete_object_list_key] = True
                    nodes_to_update.remove(p)
                    break

        return Ontotology(graph)
