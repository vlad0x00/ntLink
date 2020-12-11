#!/usr/bin/env python3
"""
Stitch together paths with information from n-sweep from abyss-scaffold
"""
__author__ = "laurencoombe"

import argparse
import datetime
import re
import sys
import os
from collections import defaultdict
import igraph as ig
import numpy as np
import ntlink_utils
from PathNode import PathNode

class NtLinkPath:
    "Instance of ntLink stitch path phase"

    @staticmethod
    def read_scaffold_graph(in_graph_file):
        "Reads in a scaffold graph in dot format"

        graph = ig.Graph(directed=True)

        vertices = set()
        edges = defaultdict(dict)  # source -> target -> EdgeInfo

        node_re = re.compile(r'\"(\S+[+-])\"\s+\[l\=\d+\]')
        edge_re = re.compile(r'\"(\S+[+-])\"\s+\-\>\s+\"(\S+[+-])\"\s+\[d\=(\-?\d+)\s+e\=\d+\s+n\=(\d+)\]')

        past_header = False

        with open(in_graph_file, 'r') as in_graph:
            for line in in_graph:
                line = line.strip()
                if not past_header:
                    past_header = True
                    continue
                node_match = re.search(node_re, line)
                if node_match:
                    vertices.add(node_match.group(1))
                    continue

                edge_match = re.search(edge_re, line)
                if edge_match:
                    source, target, gap_est, num_links = edge_match.group(1), edge_match.group(2), \
                                                         edge_match.group(3), edge_match.group(4)
                    edges[source][target] = (int(gap_est), int(num_links))
                elif line != "}":
                    print("Error! Unexpected line in input dot file:", line)
                    sys.exit(1)

        formatted_edges = [(s, t) for s in edges for t in edges[s]]
        graph.add_vertices(list(vertices))
        graph.add_edges(formatted_edges)

        edge_attributes = {ntlink_utils.edge_index(graph, s, t): {'d': edges[s][t][0],
                                                                  "n": edges[s][t][1]}
                           for s in edges for t in edges[s]}
        graph.es()["d"] = [edge_attributes[e]['d'] for e in sorted(edge_attributes.keys())]
        graph.es()["n"] = [edge_attributes[e]['n'] for e in sorted(edge_attributes.keys())]

        return graph

    @staticmethod
    def read_paths(path_filename):
        "Read paths into graph data structure"
        #191361	188729-5+ 21N 40000+
        print(datetime.datetime.today(), ": Building path graph", file=sys.stderr)

        graph = ig.Graph(directed=True)

        gap_re = re.compile(r'(\d+)N')

        vertices = set()
        edges = defaultdict(dict)

        with open(path_filename, 'r') as path_file:
            for path in path_file:
                path_id, path_sequence = path.strip().split("\t")
                path_sequence = path_sequence.split(" ")
                for i, j, k in zip(path_sequence, path_sequence[1:], path_sequence[2:]):
                    gap_match = re.search(gap_re, j)
                    if not gap_match:
                        continue # Only continue if it is 2 scaffolds with gap between

                    # Add vertices
                    vertices.add(i)
                    vertices.add(k)
                    vertices.add(ntlink_utils.reverse_scaf_ori(i))
                    vertices.add(ntlink_utils.reverse_scaf_ori(k))

                    # Add edges
                    assert i not in edges and k not in edges[i]
                    edges[i][k] = (gap_match.group(1), path_id)
                    edges[ntlink_utils.reverse_scaf_ori(k)][ntlink_utils.reverse_scaf_ori(i)] = \
                        (gap_match.group(1), path_id)

        graph.add_vertices(list(vertices))

        formatted_edges = [(s, t) for s in edges for t in edges[s]]
        graph.add_edges(formatted_edges)

        edge_attributes = {ntlink_utils.edge_index(graph, s, t): {'d': edges[s][t][0],
                                                                  "path_id": edges[s][t][1]}
                           for s in edges for t in edges[s]}
        graph.es()["d"] = [edge_attributes[e]['d'] for e in sorted(edge_attributes.keys())]
        graph.es()["path_id"] = [edge_attributes[e]['path_id'] for e in sorted(edge_attributes.keys())]

        return graph

    @staticmethod
    def are_end_vertices(source, target, path_graph):
        "Checks if both the source and target are end vertices"
        return path_graph.vs()[ntlink_utils.vertex_index(path_graph, source)].outdegree() == 0 and \
               path_graph.vs()[ntlink_utils.vertex_index(path_graph, target)].indegree() == 0

    @staticmethod
    def is_end_vertex(graph, node, mode="out"):
        "Returns true if the given node is an end vertex in mode specified"
        assert mode in ["out", "in"]
        if mode == "out":
            return graph.vs()[ntlink_utils.vertex_index(graph, node)].outdegree() == 0
        return graph.vs()[ntlink_utils.vertex_index(graph, node)].indegree() == 0

    @staticmethod
    def find_new_transitive_edges(edges, path, scaffold_graph, s, t):
        "Given a path, tally transitive edges"
        source_idx = path.index(s)
        source_vertices = path[:source_idx+1]
        target_vertices = path[source_idx+1:]
        for source in source_vertices:
            for target in target_vertices:
                if source == s and target == t:
                    continue
                rev_s, rev_t = ntlink_utils.reverse_scaf_ori(source), ntlink_utils.reverse_scaf_ori(target)
                if scaffold_graph.are_connected(source, target):
                    continue
                edges.add((source, target))
                edges.add((rev_t, rev_s))


    def add_transitive_support(self, scaffold_graph, path_sequence, path_graph, neighbourhood=4):
        "Given a path sequence and a graph, add all transitive edges"
        edges = set()
        path_sequence = [node for node in path_sequence if "N" not in node] # !! TODO - Generalize
        for idx, s_t in enumerate(zip(path_sequence, path_sequence[1:])):
            s, t = s_t
            if not (ntlink_utils.has_vertex(path_graph, s) and ntlink_utils.has_vertex(path_graph, t) and
                    path_graph.are_connected(s, t)):
                start, end = max(0, idx - neighbourhood), min(len(path_sequence), idx + neighbourhood + 2)
                path_neighbourhood = path_sequence[start:end] # 1 target, 1 past
                self.find_new_transitive_edges(edges, path_neighbourhood, scaffold_graph, s, t)

        return edges

    def read_alternate_pathfile(self, n, path_graph, new_vertices, new_edges, scaffold_graph):
        "Read through alt abyss-scaffold output file, adding potential new edges"
        filename = "{}.n{}.abyss-scaffold.path".format(self.args.p, n)

        print("Reading {}".format(filename), file=sys.stderr)
        gap_re = re.compile(r'^(\d+)N$')
        trans_edges = set()

        if not os.path.exists(filename):
            print("{} does not exist, skipping.".format(filename), file=sys.stderr)
            return set()
        with open(filename, 'r') as fin:
            for path in fin:
                _, path_sequence = path.strip().split("\t")
                path_sequence = path_sequence.split(" ")
                trans_edges = set.union(trans_edges, self.add_transitive_support(scaffold_graph,
                                                                                 path_sequence, path_graph))
                for i, j, k in zip(path_sequence, path_sequence[1:], path_sequence[2:]):
                    gap_match = re.search(gap_re, j)
                    if not gap_match:
                        continue
                    source, target, gap_est = i, k, int(gap_match.group(1))
                    if ntlink_utils.has_vertex(path_graph, source) and \
                            ntlink_utils.has_vertex(path_graph, target):
                        if path_graph.are_connected(source, target):
                            continue # continue if the source/target are already connected
                        if self.are_end_vertices(source, target, path_graph):
                            self.add_path_edges(gap_est, i, k, new_edges)

                    if ntlink_utils.has_vertex(path_graph, source) and \
                            not ntlink_utils.has_vertex(path_graph, target) and \
                            self.is_end_vertex(path_graph, source, mode="out"):
                        new_vertices.add(target)
                        new_vertices.add(ntlink_utils.reverse_scaf_ori(target))
                        self.add_path_edges(gap_est, source, target, new_edges)

                    if ntlink_utils.has_vertex(path_graph, target) and \
                            not ntlink_utils.has_vertex(path_graph, source) and \
                            self.is_end_vertex(path_graph, target, mode="in"):
                        new_vertices.add(source)
                        new_vertices.add(ntlink_utils.reverse_scaf_ori(source))
                        self.add_path_edges(gap_est, source, target, new_edges)

                    if not ntlink_utils.has_vertex(path_graph, source) and \
                            not ntlink_utils.has_vertex(path_graph, target):
                          #  (source in new_vertices or target in new_vertices):
                        new_vertices.add(source)
                        new_vertices.add(ntlink_utils.reverse_scaf_ori(source))

                        new_vertices.add(target)
                        new_vertices.add(ntlink_utils.reverse_scaf_ori(target))

                        self.add_path_edges(gap_est, source, target, new_edges)
        return trans_edges

    @staticmethod
    def add_path_edges(gap_dist, source, target, new_edges):
        "Add the new path edges in both orientations to given graph"
        if (source not in new_edges and target not in new_edges[source]) or \
                (source in new_edges and target not in new_edges[source]):
            new_edges[source][target] = [gap_dist]
        else:
            new_edges[source][target].append(gap_dist)

        rev_i, rev_k = ntlink_utils.reverse_scaf_ori(source), ntlink_utils.reverse_scaf_ori(target)
        if (rev_k not in new_edges and rev_i not in new_edges[rev_k]) or \
                (rev_k in new_edges and rev_i not in new_edges[rev_k]):
            new_edges[rev_k][rev_i] = [gap_dist]
        else:
            new_edges[rev_k][rev_i].append(gap_dist)

    def read_alternate_pathfiles(self, path_graph, scaffold_graph):
        "Read through alt abyss-scaffold output files, adding potential new edges for paths"
        new_edges = defaultdict(dict)
        new_vertices = set()
        new_scaffold_edges = set()

        for i in range(self.args.min_n, self.args.max_n + 1):
            new_trans_edges = self.read_alternate_pathfile(i, path_graph, new_vertices, new_edges, scaffold_graph)
            new_scaffold_edges = set.union(new_scaffold_edges, new_trans_edges)

        path_graph.add_vertices(list(new_vertices))

        formatted_edges = []
        formatted_attributes = []
        before_edge = path_graph.ecount()

        for new_source in new_edges:
            for new_target in new_edges[new_source]:
                formatted_edges.append((new_source, new_target))
                d = new_edges[new_source][new_target]
                formatted_attributes.append(d)
#                path_graph.add_edge(new_source, new_target, d=int(np.median(d)), path_id="new", n=len(d))
        path_graph.add_edges(formatted_edges)
        for i in range(before_edge, path_graph.ecount()):
            d = formatted_attributes[i - before_edge]
            path_graph.es()[i]["d"] = int(np.median(d))
            path_graph.es()[i]["n"] = len(d)
            path_graph.es()[i]["path_id"] = "new"

        scaffold_graph.add_edges(list(new_scaffold_edges))

    @staticmethod
    def linearize_graph(graph):
        "Filter the graph to linearize it"
        in_branch_nodes = [node.index for node in graph.vs() if node.indegree() > 1]
        to_remove_edges = set()
        for node in in_branch_nodes:
            max_weight_edge, max_weight = None, None
            incident_edges = graph.incident(node, mode=ig.IN) # pylint: disable=no-member
            if all([graph.es()[edge]['path_id'] == "new" for edge in incident_edges]):
                max_weight = max([graph.es()[edge]['n'] for edge in incident_edges])
                max_weight_edges = [edge for edge in incident_edges if graph.es()[edge]['n'] == max_weight]
                if len(max_weight_edges) == 1:
                    max_weight_edge = max_weight_edges[0]
            for edge in incident_edges:
                if edge != max_weight_edge and graph.es()[edge]['path_id'] == "new":
                    to_remove_edges.add(edge)

        out_branch_nodes = [node.index for node in graph.vs() if node.outdegree() > 1]
        for node in out_branch_nodes:
            max_weight_edge, max_weight = None, None
            incident_edges = graph.incident(node, mode=ig.OUT) # pylint: disable=no-member
            if all([graph.es()[edge]['path_id'] == "new" for edge in incident_edges]):
                max_weight = max([graph.es()[edge]['n'] for edge in incident_edges])
                max_weight_edges = [edge for edge in incident_edges if graph.es()[edge]['n'] == max_weight]
                if len(max_weight_edges) == 1:
                    max_weight_edge = max_weight_edges[0]
            for edge in incident_edges:
                if edge != max_weight_edge and graph.es()[edge]['path_id'] == "new":
                    to_remove_edges.add(edge)

        return_graph = graph.copy()
        return_graph.delete_edges(list(to_remove_edges))

        return return_graph

    @staticmethod
    def is_graph_linear(graph):
        "Given a graph, return True if all the components are linear"
        for component in graph.components(mode="weak"):
            component_graph = graph.subgraph(component)
            if not all(u.indegree() < 2 for u in component_graph.vs()):
                return False
            if not all(u.outdegree() < 2 for u in component_graph.vs()):
                return False
        return True

    @staticmethod
    def format_path_contigs(path, component_graph):
        "Given a path (sequence of oriented contigs), format to a path of PathNode"
        return_path = []
        for ctga, ctgb in zip(path, path[1:]):
            ctga_name, ctga_ori = ctga[:-1], ctga[-1]
            edge_index = ntlink_utils.edge_index(component_graph, ctga, ctgb)
            gap_estimate = component_graph.es()[edge_index]['d']
            return_path.append(PathNode(contig=ctga_name, ori=ctga_ori,
                                        gap_size=gap_estimate))
        last_ctg_name, last_ctg_ori = path[-1][:-1], path[-1][-1]
        return_path.append(PathNode(contig=last_ctg_name, ori=last_ctg_ori))
        return return_path

    def find_paths_process(self, component):
        "Find paths given a component of the graph"
        return_paths = []
        component_graph = NtLinkPath.gin.subgraph(component)
        source_nodes = [node.index for node in component_graph.vs() if node.indegree() == 0]
        if len(source_nodes) == 1:
            target_nodes = [node.index for node in component_graph.vs() if node.outdegree() == 0]
            assert len(target_nodes) == 1
            source, target = source_nodes[0], target_nodes[0]
            path = component_graph.get_shortest_paths(source, target)[0]
            num_edges = len(path) - 1
            if len(path) == len(component_graph.vs()) and \
                    num_edges == len(component_graph.es()) and len(path) == len(set(path)):
                # All the nodes/edges from the graph are in the simple path, no repeated nodes
                path = ntlink_utils.convert_path_index_to_name(component_graph, path)
                ctg_path = self.format_path_contigs(path, component_graph)
                return_paths.append(ctg_path)

        return return_paths

    @staticmethod
    def remove_duplicate_paths(paths):
        "Removes paths that are reverse complements of each other or have dup contigs"
        visited = set()
        return_paths = []
        for path in paths:
            if not any([node.contig in visited for node in path]):
                return_paths.append(path)
            for node in path:
                visited.add(node.contig)
        return return_paths

    def find_paths(self, graph):
        "Finds paths through input scaffold graph"
        print(datetime.datetime.today(), ": Finding paths", file=sys.stderr)
        NtLinkPath.gin = graph
        components = graph.components(mode="weak")
        print("\nTotal number of components in graph:", len(components), "\n", sep=" ", file=sys.stderr)

        paths = [self.find_paths_process(component) for component in components]

        paths_return = [path for path_list in paths for path in path_list]
        paths_return = self.remove_duplicate_paths(paths_return)
        return paths_return

    @staticmethod
    def has_transitive_support(edge, path_graph, scaffold_graph):
        "Returns True if edge has transitive support"
        source, target = ntlink_utils.vertex_name(path_graph, edge.source), \
                         ntlink_utils.vertex_name(path_graph, edge.target)
        source_pass, target_pass = False, False
        path_size = len(path_graph.vs())
        source_in_neighbourhood = [ntlink_utils.vertex_name(path_graph, idx)
                                   for idx in path_graph.neighborhood(source, order=path_size, mode="in")]
        target_out_neighbourhood = [ntlink_utils.vertex_name(path_graph, idx)
                                    for idx in path_graph.neighborhood(target, order=path_size, mode="out")]
        for test_source in source_in_neighbourhood:
            for test_target in target_out_neighbourhood:
                if test_source == source and test_target == target:
                    continue
                if scaffold_graph.are_connected(test_source, test_target):
                    if test_source == source or test_target == target:
                        if test_source == source:
                            source_pass = True
                        if test_target == target:
                            target_pass = True
                        if source_pass and target_pass:
                            return True
                    else:
                        return True
        return False

    def transitive_filter(self, path_graph, scaffold_graph):
        "Filter out edges without any transitive support"
        edges_to_remove = set()
        for edge in path_graph.es():
            if edge["path_id"] != "new":
                continue
            if not self.has_transitive_support(edge, path_graph, scaffold_graph):
                edges_to_remove.add(edge.index)

        new_graph = path_graph.copy()
        new_graph.delete_edges(list(edges_to_remove))
        return new_graph


    @staticmethod
    def print_directed_graph(graph, out_prefix):
        "Prints the directed scaffold graph in dot format"
        out_graph = out_prefix + ".scaffold-paths.dot"
        outfile = open(out_graph, 'w')
        print(datetime.datetime.today(), ": Printing graph", out_graph, sep=" ", file=sys.stderr)

        outfile.write("digraph G {\n")

        for node in graph.vs():
            node_label = "\"{scaffold}\"\n".\
                format(scaffold=node['name'])
            outfile.write(node_label)

        for edge in graph.es():
            if 'n' in edge.attributes():
                edge_str = "\"{source}\" -> \"{target}\" [d={d} n={n} path={id}]\n".\
                    format(source=ntlink_utils.vertex_name(graph, edge.source),
                           target=ntlink_utils.vertex_name(graph, edge.target),
                           d=int(edge['d']), n=edge['n'], id=edge['path_id'])
            else:
                edge_str = "\"{source}\" -> \"{target}\" [d={d} path={id}]\n".\
                    format(source=ntlink_utils.vertex_name(graph, edge.source),
                           target=ntlink_utils.vertex_name(graph, edge.target),
                           d=int(edge['d']), id=edge['path_id'])
            outfile.write(edge_str)

        outfile.write("}\n")

    @staticmethod
    def print_directed_graph_scaffold(graph, out_prefix):
        "Prints the directed scaffold graph in dot format"
        out_graph = out_prefix + ".scaffold-post-trans-add.dot"
        outfile = open(out_graph, 'w')
        print(datetime.datetime.today(), ": Printing graph", out_graph, sep=" ", file=sys.stderr)

        outfile.write("digraph G {\n")

        for node in graph.vs():
            node_label = "\"{scaffold}\"\n".\
                format(scaffold=node['name'])
            outfile.write(node_label)

        for edge in graph.es():
            edge_str = "\"{source}\" -> \"{target}\"\n".\
                format(source=ntlink_utils.vertex_name(graph, edge.source),
                       target=ntlink_utils.vertex_name(graph, edge.target))
            outfile.write(edge_str)

        outfile.write("}\n")

    def main(self):
        "Run ntLink stitch paths stage"
        print("Running ntLink stitch paths stage...\n", file=sys.stderr)

        path_graph = self.read_paths(self.args.PATH)

        scaffold_graph = self.read_scaffold_graph(self.args.g)

        self.read_alternate_pathfiles(path_graph, scaffold_graph)

        self.print_directed_graph(path_graph, self.args.p + ".out")


        path_graph = self.linearize_graph(path_graph)
        assert self.is_graph_linear(path_graph)

        self.print_directed_graph(path_graph, self.args.p + ".out-pre-trans")
        self.print_directed_graph_scaffold(scaffold_graph, self.args.p + ".out-scaffold_graph")
        if self.args.transitive:
            print("Checking for transitive support...\n", file=sys.stderr)
            path_graph = self.transitive_filter(path_graph, scaffold_graph)

        NtLinkPath.gin = path_graph

        self.print_directed_graph(path_graph, self.args.p + ".out-post-trans")
        paths = self.find_paths(path_graph)

        path_id = 0
        for path in paths:
            path_list = []
            for node in path:
                path_list.append(node.get_ori_contig())
                if node.get_gap() is not None:
                    path_list.append(node.get_gap())
            if len(path_list) < 2:
                continue
            path_str = " ".join(path_list)
            print("ntLink_{path_id}".format(path_id=path_id), path_str, sep="\t")
            path_id += 1




    @staticmethod
    def parse_arguments():
        "Parse ntLink arguments"
        parser = argparse.ArgumentParser(description="ntLink: Scaffolding genome assemblies using long reads. "
                                                     "This step further stitches together paths.")
        parser.add_argument("PATH", help="abyss-scaffold best n path file")
        parser.add_argument("--min_n", help="Minimum 'n' specified to abyss-scaffold", required=True, type=int)
        parser.add_argument("--max_n", help="Maximum 'n' specified to abyss-scaffold", required=True, type=int)
        parser.add_argument("-g", help="Unfiltered scaffold graph dot file", required=True, type=str)
        parser.add_argument("-a", help="Ratio of best to second best edge to create potential connection",
                            required=False, default=0.3, type=float)
        parser.add_argument("-p", help="Output file prefix", required=False, default="out", type=str)
        parser.add_argument("--transitive", help="Require transitive support for edges?", action="store_true")

        return parser.parse_args()

    def __init__(self):
        "Create new ntLink_path instance"
        self.args = self.parse_arguments()

def main():
    "Run ntLink stitch paths stage"
    NtLinkPath().main()


if __name__ == "__main__":
    main()
