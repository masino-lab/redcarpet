__author__ = 'Aaron J Masino'

import sys
from rollup.models import rollup
from rollup.models import ontology
from rollup.utils import config_helper
from rollup.utils import collections
from functools import partial


def main(argv=None):

    if argv is None:
        argv = sys.argv

    if len(argv) < 2:
        print("Configuration file path must be provided.\nExiting now.")

    else:
        config_path = argv[1]
        print("Running with config: {0}".format(config_path))
        config = config_helper.loadConfig(config_path)
        input_files = config_helper.ConfigSectionMap(config, "Input_Files")
        output_files = config_helper.ConfigSectionMap(config, "Output_Files")

        print("Creating ontology from:\n{0}\n{1}".format(input_files['FILE_ONTOLOGY'],
                                                         input_files['FILE_ANNOTATIONS']))

        ont_factory = ontology.OntologyFactory()

        ont = ont_factory.build_ontology_from_files(input_files['FILE_ONTOLOGY'], input_files['FILE_ANNOTATIONS'])

        print("Starting rollup ...")
        rollup_options = config_helper.ConfigSectionMap(config, "Rollup_Options")
        checkpoints = None
        checkpoint_hook = None
        if "CHECK_POINTS" in rollup_options:
            checkpoints = config_helper.getListInt(config, "Rollup_Options", "CHECK_POINTS")
            checkpoint_hook = partial(checkpoint_save,
                                      ont=ont,
                                      input_files=input_files,
                                      output_files=output_files)

        rollups, rollup_levels, best_means, best_stdevs = rollup.rollup(ont,
                      int(rollup_options['TOTAL_ANNOTATORS_AFTER_ROLLUP']),
                      int(rollup_options['MAXIMUM_ITERATIONS']),
                      int(rollup_options['PRINT_STATUS_FREQ']),
                      checkpoints, checkpoint_hook)

        print("Storing output ...")
        checkpoint_save(int(rollup_options['TOTAL_ANNOTATORS_AFTER_ROLLUP']),
                        rollups, rollup_levels, best_means, best_stdevs,
                        ont, input_files, output_files)

        print("Rollup.main() completed.")


def checkpoint_save(annotator_count,
                    rollups, rollup_levels, best_means, best_stdevs,
                    ont, input_files, output_files):
    print("Storing output for checkpoint {0}".format(annotator_count))
    if 'FILE_ROLLUP' in output_files:
        rollup.serialize_rollups(rollups, output_files['FILE_ROLLUP'].format(annotator_count))
    if 'FILE_ROLLUP_LEVELS' in output_files:
        rollup.serialzie_rollup_levels(rollup_levels, output_files['FILE_ROLLUP_LEVELS'].format(annotator_count))
    if 'FILE_BEST_MEAN_IC' in output_files:
        collections.serialize_list(best_means, output_files['FILE_BEST_MEAN_IC'].format(annotator_count))
    if 'FILE_BEST_STDEV_IC' in output_files:
        collections.serialize_list(best_stdevs, output_files['FILE_BEST_STDEV_IC'].format(annotator_count))
    if 'FILE_ONTOLOGY' in output_files:
        ont.serialize_nodes(output_files['FILE_ONTOLOGY'].format(annotator_count))
    if 'FILE_ANNOTATIONS' in output_files:
        # need to reload original annotations because the ontology has been mutated in rollup
        original_annotations = {}
        with open(input_files['FILE_ANNOTATIONS'], 'r') as f:
            for line in f.readlines():
                data = line.split(":")
                cid = data[0].strip()
                if len(data) > 1:
                    objects = [x.strip() for x in data[1].split(",")]
                    original_annotations[cid] = objects
        rolled_annotations = rollup.map_annotations_with_rollup(rollups, original_annotations)
        collections.serialize_dict_of_lists(rolled_annotations, output_files['FILE_ANNOTATIONS'].format(annotator_count))

if __name__ == '__main__':
    sys.exit(main())