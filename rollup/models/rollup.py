__author__ = 'Aaron J Masino'

import numpy as np
import time
from rollup.utils import collections


def rollup(ontology,
           desired_annotators = 250,
           max_iters = 50000,
           print_freq = 500,
           checkpoints = None,
           checkpoint_hook = None
           ):
    """
    Performs a rollup on ontology using a greedy search on current leaves in the ontology
    by selecting the leaf whose elimination will yield the minimum standard deviation of
    the average information content of all concepts that directly annotate an object

    WARNING: THIS WILL MUTATE THE INPUT ONTOLOGY GRAPH BY REMOVING LEAF NODES THAT ARE ROLLED UP,
    AND ADDING ANNOTATIONS TO THE CONCEPTS TO WHICH DESCENDANT CONCEPTS ARE ROLLED TO

    :param ontology: an instance of rollup.ontology.Ontology
    :param desired_annotators: the number of direct annotators after rollup
    :param max_iters: maximum number of iterations allowed for rollup
    :param print_freq: frequency in iterations to print status
    :param checkpoints: list of integers of number of annotators at which checkpoint_hook should be called
    :param checkpoint_hook: callable that accepts position args: annotator_count, rollups, rollup_levels, best_lambdas, best_psis
    :return: (rollup, rollup_levels, best_lambdas, best_psis)
            rollup - dictionary - keys are concepts in the original graph, values are the concepts to which the
                                   given concept represented by the key is rolled up to. For concepts that do not
                                   get rolled up, the key and value are identical
            rollup_levels - dictionary - keys are concept ids from ontology graph, values are the highest number
                                         of edges in the original graph between the concept and the concepts it was
                                         rolled to
            best_lambdas - list of mean direct annotator IC over all algorithm iterations
            best_psis - list of stdev of direct annotator IC over all algorithm iterations
    """
    N = ontology.total_annotated_objects()
    D = ontology.total_annotators()
    annotator_ICs = ontology.annotators_information_content(N)
    Gamma = np.sum([x for x in annotator_ICs.values()])
    Lambda = Gamma / float(D)
    Psi = ic_stdev(annotator_ICs.values(), Lambda, D)

    print("Initial Direct Annotator Count:\t{0}".format(D))
    print("Initial Direct Annotator Mean IC:\t{0}\n".format(Lambda))
    print("Initial Direct Annotator IC Stdev:\t{0}\n".format(Psi))

    # initialize variables for logging
    best_lambdas = [Lambda]
    best_gammas = [Gamma]
    best_psis = [Psi]
    leaf_counts = []
    annotator_counts = []
    iterations = 0
    rollups = {}
    rollup_levels = {}

    t0 = time.time()
    while D > desired_annotators and iterations < max_iters:
        leaf_to_roll = None
        best_Gamma = 0.0
        best_Psi = float("inf")
        best_D = D
        leaves = ontology.leaf_nodes()
        if not leaves:
            print("WARNING: NO LEAVES FOUND IN GRAPH")
        iterations += 1
        parent_is_object_annotator = {}
        leaf_count = 0
        for leaf in leaves:
            leaf_count += 1
            tmp_Gamma = Gamma
            parents = ontology.parent_concepts(leaf)

            # store leaf attributes to restore later
            leaf_ic = ontology.information_content(leaf, N)

            for p in parents:
                p_node = ontology.graph.node[p]
                # need to store parent's current is_visit_annotator
                parent_is_object_annotator[p] = p_node[ontology.is_direct_annotator_key]
                if not p_node[ontology.is_direct_annotator_key]:
                    # temporarily add parent to list of annotators for rollup and add ic to Gamma
                    pic = ontology.information_content(p, N)
                    annotator_ICs[p] = pic
                    tmp_Gamma += pic

            # temporarily remove leaf from annotator_ICs for stdev computation
            del annotator_ICs[leaf]

            tmp_Gamma -= leaf_ic
            tmp_D = len(annotator_ICs)
            tmp_Lambda = tmp_Gamma / float(tmp_D)
            tmp_Psi = ic_stdev(annotator_ICs.values(), tmp_Lambda, tmp_D)
            if (tmp_Lambda < 0):
                print("WARNING: NEGATIVE TMP_LAMBDA")

            # store current best values
            if tmp_Psi < best_Psi:
                best_Psi = tmp_Psi
                best_Gamma = tmp_Gamma
                leaf_to_roll = leaf
                best_D = tmp_D

            # restore leaf and parents to current state
            annotator_ICs[leaf] = leaf_ic

            for p in parents:
                if not parent_is_object_annotator[p]:
                    del annotator_ICs[p]

                    # END for leaf in leaves

        # make sure there is a leaf to roll
        if leaf_to_roll == None:
            print("WARNING: LEAF_TO_ROLL IS NONE")
            break

        # update leaf_to_roll parents
        leaf_parents = ontology.parent_concepts(leaf_to_roll)
        for p in leaf_parents:
            p_node = ontology.graph.node[p]
            parent_is_object_annotator = p_node[ontology.is_direct_annotator_key]
            if not parent_is_object_annotator:
                p_node[ontology.is_direct_annotator_key] = True
                annotator_ICs[p] = ontology.information_content(p, N)

        # roll up leaf_to_roll - remove it from graph and annotator list
        ontology.graph.remove_node(leaf_to_roll)
        del annotator_ICs[leaf_to_roll]

        # update Gamma, N, D
        D = best_D
        Gamma = best_Gamma
        best_gammas.append(Gamma)
        Lambda = Gamma / float(D)
        best_lambdas.append(Lambda)
        Psi = best_Psi
        best_psis.append(Psi)
        leaf_counts.append(leaf_count)
        annotator_counts.append(D)
        if iterations % print_freq == 0:
            print("Iteration:\t{0}\nD (annotators):\t{1}\nLambda:\t{2}\nPsi:\t{3}\nLeaf count:\t{4}"
                  .format(iterations, D, Lambda, Psi, leaf_count))

        # store roll up as dict{rolled_child:parents}. Requires a check to determine if leaf_to_roll is in
        # any of the values of the dict in which case the key will have to be assigned to new parent
        prev_corrected_levels = []
        for k, obj_list in rollups.items():
            if leaf_to_roll in obj_list:
                if k not in prev_corrected_levels:
                    rollup_levels[k] += 1
                    prev_corrected_levels.append(k)
                obj_list.remove(leaf_to_roll)
                for p in leaf_parents:
                    if p not in obj_list:
                        obj_list.append(p)

        rollups[leaf_to_roll] = leaf_parents
        rollup_levels[leaf_to_roll] = 1
        t1 = time.time()
        tdelta = t1 - t0
        if iterations % print_freq == 0:
            print("Reduction of D to {0} to {1} seconds".format(D, tdelta))

        if D in checkpoints:
            tmp_rollups = rollups.copy()
            tmp_rollup_levels = rollup_levels.copy()
            rolled_cids = list(tmp_rollups.keys())
            for a in ontology.annotators():
                if a not in rolled_cids:
                    tmp_rollups[a] = [a]
                    tmp_rollup_levels[a] = 0
            checkpoint_hook(D, tmp_rollups, tmp_rollup_levels, best_lambdas, best_psis)


    # need to add concepts that were annotators in the original data and were NOT rolled up to the rollup dictionary
    # this will be needed to differentiate these concepts from concepts that appear in new data that were not part of
    # the ontology segment represented by the dataset used to rollup concepts
    rolled_cids = list(rollups.keys())
    for a in ontology.annotators():
        if a not in rolled_cids:
            rollups[a] = [a]
            rollup_levels[a] = 0

    tf = time.time()
    tdelta = tf - t0
    print("Total time: {0} seconds".format(tdelta))

    return (rollups, rollup_levels, best_lambdas, best_psis)

def serialize_rollups(rollups, file_path):
    """
    stores rollup to file
    :param rollups: rollup dictionary returned by rollup method
    :param file_path: location to store data
    :return: None
    """
    with open(file_path, 'a+') as f:
        first_line = True
        for k, obj_list in rollups.items():
            if not first_line:
                line = "\n{0}:".format(k)
            else:
                line = "{0}:".format(k)
                first_line = False
            for v in obj_list:
                line = "{0}{1},".format(line, v)
            line = line[0:-1]
            f.write(line)


def ic_stdev(ic_vals, mean_ic, total_annotators):
    return np.sqrt(np.sum([(x - mean_ic) ** 2 for x in ic_vals]) / float(total_annotators))


def serialzie_rollup_levels(rollup_levels, file_path):
    """
    stores rollup levels to file
    :param rollup_levels: rollup_levels dict returned by rollup method
    :param file_path: location to store data
    :return: None
    """
    with open(file_path, 'a+') as f:
        first_line = True
        for k, v in rollup_levels.items():
            if first_line:
                line = "{0},{1}".format(k, v)
                first_line = False
            else:
                line = "\n{0},{1}".format(k, v)
            f.write(line)


def map_annotations_with_rollup(rollups, unrolled_annotation_dict):
    rolled_annotations_dict = {}
    for cid, obj_list in unrolled_annotation_dict.items():
        rids = rollups[cid]
        for rid in rids:
            if rid in rolled_annotations_dict:
                rolled_annotations_dict[rid] = collections.merge_lists(rolled_annotations_dict[rid], obj_list)
            else:
                rolled_annotations_dict[rid] = obj_list
    return rolled_annotations_dict

