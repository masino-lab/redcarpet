__author__ = 'Aaron J Masino'


def merge_lists(l1, l2):
    return [z for z in set(l1).union(set(l2))]

def serialize_list(l, file_path):
    """
    stores list as csv line
    :param l:
    :param file_path:
    :return: None
    """
    if l:
        with open(file_path, 'a+') as f:
            line = l[0]
            if len(l) > 1:
                for v in l[1:]:
                    line = "{0},{1}".format(line, v)
            f.write(line)
    else:
        print("WARNING: Empty list passed to serialize_list method.")


def serialize_dict_of_lists(d, file_path):
    first_line = True
    with open(file_path, 'a+') as f:
        for key, l in d.items():
            line = "{0}:{1}".format(key, l[0])
            if len(l) > 1:
                for o in l[1:]:
                    line = "{0},{1}".format(line, o)
            if first_line:
                first_line = False
            else:
                line = "\n{0}".format(line)
            f.write(line)
