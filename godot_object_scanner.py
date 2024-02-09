#!/usr/bin/env python

import sys
from dataclasses import dataclass
import re
import copy

ext_resource_re = re.compile("ExtResource\(\"([^\"]+)\"\)")
sub_resource_re = re.compile("SubResource\(\"([^\"]+)\"\)")

def get_or_none(values, name):
    try:
        value = values[name]
        del values[name]
    except KeyError:
        return None
    return value

@dataclass(frozen=True)
class GodotReference:
    value : str
    ref_type : type
    res : ("GodotNode", "GodotExtReference", "GodotSubReference", str)

@dataclass
class GodotScene:
    load_steps : str | None
    res_format : str | None
    uid : str | None
    excess : dict
    values : dict

    def __init__(self, linedict : dict):
        self.load_steps = get_or_none(linedict, 'load_steps')
        self.res_format = get_or_none(linedict, 'format')
        self.uid = get_or_none(linedict, 'uid')
        self.excess = linedict
        self.values = {}
        self.refs = []

    def add_ref(self, ref : GodotReference):
        self.refs.append(ref)

    def __str__(self):
        string = "[gd_scene"
        if self.load_steps is not None:
            string += f" load_steps={self.load_steps}"
        if self.res_format is not None:
            string += f" format={self.res_format}"
        if self.uid is not None:
            string += f" uid={self.uid}"
        for item in self.excess.keys():
            string += f" {item}={self.excess[item]}"
        string += "]\n"
        for item in self.values.keys():
            string += f"{item} = {self.values[item]}\n"
        return string


@dataclass
class GodotResource:
    res_type : str | None
    load_steps : str | None
    res_format : str | None
    uid : str | None
    excess : dict
    values : dict

    def __init__(self, linedict : dict):
        self.res_type = get_or_none(linedict, 'type')
        self.load_steps = get_or_none(linedict, 'load_steps')
        self.res_format = get_or_none(linedict, 'format')
        self.uid = get_or_none(linedict, 'uid')
        self.excess = linedict
        self.values = {}
        self.refs = []

    def add_ref(self, ref : GodotReference):
        self.refs.append(ref)

    def __str__(self):
        string = "[gd_resource"
        if self.res_type is not None:
            string += f" type={self.res_type}"
        if self.load_steps is not None:
            string += f" load_steps={self.load_steps}"
        if self.res_format is not None:
            string += f" format={self.res_format}"
        if self.uid is not None:
            string += f" uid={self.uid}"
        for item in self.excess.keys():
            string += f" {item}={self.excess[item]}"
        string += "]\n"
        return string

    # this one is weird and special
    def str_end(self):
        string = "[resource]\n"
        for item in self.values.keys():
            string += f"{item} = {self.values[item]}\n"
        return string

@dataclass
class GodotExtResource:
    res_type : str | None
    uid : str | None
    path : str | None
    excess : dict
    values : dict

    def __init__(self, linedict : dict):
        self.res_type = get_or_none(linedict, 'type')
        self.uid = get_or_none(linedict, 'uid')
        self.path = get_or_none(linedict, 'path')
        self.name = get_or_none(linedict, 'id')
        if self.name is not None:
            self.name = self.name[1:-1]
        self.excess = linedict
        self.values = {}
        self.refs = []

    def add_ref(self, ref : GodotReference):
        self.refs.append(ref)

    def __str__(self):
        string = "[ext_resource"
        if self.res_type is not None:
            string += f" type={self.res_type}"
        if self.uid is not None:
            string += f" uid={self.uid}"
        if self.path is not None:
            string += f" path={self.path}"
        if self.name is not None:
            string += f" id=\"{self.name}\""
        for item in self.excess.keys():
            string += f" {item}={self.excess[item]}"
        string += "]\n"
        for item in self.values.keys():
            string += f"{item} = {self.values[item]}\n"
        return string


@dataclass
class GodotSubResource:
    res_type : str | None
    excess : dict
    values : dict

    def __init__(self, linedict : dict):
        self.res_type = get_or_none(linedict, 'type')
        self.name = get_or_none(linedict, 'id')
        if self.name is not None:
            self.name = self.name[1:-1]
        self.excess = linedict
        self.values = {}
        self.refs = []

    def add_ref(self, ref : GodotReference):
        self.refs.append(ref)

    def __str__(self):
        string = "[sub_resource"
        if self.res_type is not None:
            string += f" type={self.res_type}"
        if self.name is not None:
            string += f" id=\"{self.name}\""
        for item in self.excess.keys():
            string += f" {item}={self.excess[item]}"
        string += "]\n"
        for item in self.values.keys():
            string += f"{item} = {self.values[item]}\n"
        return string


@dataclass
class GodotNode:
    name : str | None
    res_type : str | None
    parent : str | None
    excess : dict
    values : dict

    def __init__(self, linedict : dict):
        self.name = get_or_none(linedict, 'name')
        if self.name is not None:
            self.name = self.name[1:-1]
        self.res_type = get_or_none(linedict, 'type')
        self.parent = get_or_none(linedict, 'parent')
        if self.parent is not None:
            self.parent = self.parent[1:-1]
        self.excess = linedict
        self.values = {}
        self.refs = []

    def set_parent(self, parent):
        parent.add_ref(GodotReference("child", GodotNode, self))

    def add_ref(self, ref : GodotReference):
        self.refs.append(ref)

    def __str__(self):
        string = "[node"
        if self.name is not None:
            string += f" name=\"{self.name}\""
        if self.res_type is not None:
            string += f" type={self.res_type}"
        if self.parent is not None:
            string += f" parent={self.parent.name}"
        for item in self.excess.keys():
            string += f" {item}={self.excess[item]}"
        string += "]\n"
        for item in self.values.keys():
            string += f"{item} = {self.values[item]}\n"
        return string


def split_godot_object_line(line):
    try:
        kind, rest = line[1:-1].split(maxsplit=1)
    except ValueError:
        return line[1:-1], {}
    items = rest.split('=')
    values = {}
    if len(items) == 2:
        values[items[0].strip()] = items[1].strip()
    elif len(items) == 3:
        values[items[0].strip()] = items[1][:items[1].rindex(' ')].strip()
        values[items[1][items[1].rindex(' ')+1:].strip()] = items[2].strip()
    else:
        values[items[0].strip()] = items[1][:items[1].rindex(' ')].strip()
        for i in range(1, len(items)-2):
            values[items[i][items[i].rindex(' '):].strip()] = \
                items[i+1][:items[i+1].rindex(' ')+1].strip()
        values[items[-2][items[-2].rindex(' ')+1:].strip()] = items[-1].strip()

    return kind, values

def read_godot_file(file):
    contents = []
    cur = None

    for line in file:
        line = line.strip()
        # skip empty lines
        if len(line) == 0:
            continue

        # if the line is a "section" heading, figure out what it is and
        # make it in to an object
        if line[0] == '[' and line[-1] == ']':
            kind, values = split_godot_object_line(line)
            match kind:
                case 'gd_scene':
                    if cur is not None:
                        raise ValueError("Found a gd_scene not as the first entry!")
                    cur = GodotScene(values)
                    contents.append(cur)
                case 'gd_resource':
                    if cur is not None:
                        raise ValueError("Found a gd_resource not as the first entry!")
                    cur = GodotResource(values)
                    contents.append(cur)
                case 'resource':
                    if cur is None:
                        raise ValueError("First entry must be gd_scene or gd_resource!")
                    if not isinstance(contents[0], GodotResource):
                        raise ValueError("Found standalone resource section in a file not a gd_resource.")
                    if len(values) != 0:
                        raise ValueError("Found standalone resource section with values?") 
                    # seems to be a section that can occur later in the file that is
                    # additional "root" references
                    cur = contents[0]
                case 'ext_resource':
                    if cur is None:
                        raise ValueError("First entry must be gd_scene or gd_resource!")
                    cur = GodotExtResource(values)
                    contents.append(cur)
                case 'sub_resource':
                    if cur is None:
                        raise ValueError("First entry must be gd_scene or gd_resource!")
                    cur = GodotSubResource(values)
                    contents.append(cur)
                case 'node':
                    if cur is None:
                        raise ValueError("First entry must be gd_scene or gd_resource!")
                    if not isinstance(contents[0], GodotScene):
                        raise ValueError("Godot node in a file which isn't a scene!")
                    cur = GodotNode(values)
                    contents.append(cur)
        else:
            # if it's not a section heading, try to interpret it as a key/value
            # pair
            key, value = line.split('=', maxsplit=1)
            cur.values[key.strip()] = value.strip()

    # first entry [0] is guaranteed at this point to be the root entry
    # but no linkage has been made
    # the contents need to be "checked" first
    return contents

def do_build_paths(res):
    # missing reference, just return None
    if isinstance(res, str):
        return [(None, f"/{res}!!missing!!")]

    name = "root"
    try:
        name = res.name
    except AttributeError:
        pass

    # add the reference itself
    paths = [(res, f"/{name}")]

    # go through all references
    for ref in res.refs:
        # recursively get all the paths of references ahead of this resource
        newpaths = do_build_paths(ref.res)
        # prepend this resource's name and the values that point to the next
        # referenced resources
        if ref.ref_type == GodotExtResource:
            for i, newpath in enumerate(newpaths):
                newpaths[i] = (newpath[0],
                               f"/{name}/{ref.value}/ext{newpath[1]}")
        elif ref.ref_type == GodotSubResource:
            for i, newpath in enumerate(newpaths):
                newpaths[i] = (newpath[0],
                               f"/{name}/{ref.value}/sub{newpath[1]}")
        elif ref.ref_type == GodotNode:
            for i, newpath in enumerate(newpaths):
                newpaths[i] = (newpath[0],
                               f"/{name}/{ref.value}{newpath[1]}")
        # add the batch of paths to this resource's list of paths
        paths.extend(newpaths)

    return paths

def build_paths(godotfile):
    # pass the first object which should be the root
    return do_build_paths(godotfile[0])

def check_file(godotfile):
    duplicate_sub_names = []
    duplicate_ext_names = []
    sub_resources = {}
    ext_resources = {}
    nodes = None
    if isinstance(godotfile[0], GodotScene):
        nodes = {}
        # find root object and point the scene to it
        for item in godotfile:
            if isinstance(item, GodotNode):
                if item.parent is None:
                    if len(godotfile[0].refs) != 0:
                        raise ValueError("Multiple scene roots?!")
                    godotfile[0].add_ref(GodotReference("scene",
                                                        GodotNode,
                                                        item))
                    nodes["."] = item

    # categorize all the items by type and index them by name
    # don't overwrite duplciates, add them to a list
    # multiple nodes can have the same name as they singly reference their parent
    # so there's no ambiguity.
    for item in godotfile:
        if isinstance(item, GodotSubResource):
            if item.name in sub_resources:
                duplicate_sub_names.append(item.name)
            else:
                sub_resources[item.name] = item
        elif isinstance(item, GodotExtResource):
            if item.name in ext_resources:
                duplicate_ext_names.append(item.name)
            else:
                ext_resources[item.name] = item
        elif isinstance(item, GodotNode):
            nodes[item.name] = item

    missing_sub_resources = []
    missing_ext_resources = []
    missing_nodes = []
    # scan each item, if any names of any references are missing, add them to a
    # missing names list, otherwise add the object to a list of references for
    # easily path following later
    for item in godotfile:
        # if it's a node, make sure its parent is pointing to this node
        if isinstance(item, GodotNode):
            try:
                if item.parent is None:
                    continue
                item.set_parent(nodes[item.parent])
            except KeyError:
                missing_nodes.append(item.name)

        # scan each value to determine if it references anything
        for value in item.values.keys():
            match = ext_resource_re.match(item.values[value])
            if match is not None:
                ext_res = match.group(1)
                try:
                    item.add_ref(GodotReference(value,
                                                GodotExtResource,
                                                ext_resources[ext_res]))
                except KeyError:
                    item.add_ref(GodotReference(value,
                                                GodotExtResource,
                                                ext_res))
                    missing_ext_resources.append(ext_res)
            match = sub_resource_re.match(item.values[value])
            if match is not None:
                sub_res = match.group(1)
                try:
                    item.add_ref(GodotReference(value,
                                                GodotSubResource,
                                                sub_resources[sub_res]))
                except KeyError:
                    item.add_ref(GodotReference(value,
                                                GodotSubResource,
                                                ext_res))
                    missing_sub_resources.append(sub_res)

    return duplicate_ext_names, duplicate_sub_names, missing_ext_resources, missing_sub_resources, missing_nodes

def find_dupes(godotfile):
    dupes = []
    sub_dupes_lists = []
    ext_dupes_lists = []
    # look for any resources which are identical in data values
    for i, item1 in enumerate(godotfile):
        # only interested in resources
        if isinstance(item1, GodotSubResource):
            restype = GodotSubResource
            dupes_lists = sub_dupes_lists
        elif isinstance(item1, GodotExtResource):
            restype = GodotExtResource
            dupes_lists = ext_dupes_lists
        else:
            continue
        # if it's already been found as a dupe, don't add it again
        if item1.name in dupes:
            continue
        found_dupe = False
        # look only to resources ahead of this one as prior ones will already
        # have been compared before
        for item2 in godotfile[i+1:]:
            # don't bother comparing against objects that aren't of the same type
            if not isinstance(item2, restype):
                continue
            if item2 == item1:
                # keep track of all which have been a dupe to not re-add the
                # same objects again
                dupes.append(item2.name)
                # first found dupe should add a new list to the dupes list
                if not found_dupe:
                    dupes_lists.append([])
                    dupes_lists[-1].append(item1.name)
                    dupes.append(item1.name)
                    found_dupe = True
                # then add the item to the latest dupes list
                dupes_lists[-1].append(item2.name)

    return sub_dupes_lists, ext_dupes_lists

def replace_res(godotfile, newres, oldres, res_re, res_type, fmt_str):
    # find all the references to the old resource and replace them with the new
    # one
    for item in godotfile:
        for value in item.values.keys():
            match = res_re.match(item.values[value])
            if match is not None:
                matched_res = match.group(1)
                if matched_res == oldres:
                    item.values[value] = fmt_str.format(newres)

    # scan for the resource then delete it, there should only be one instance of
    # it so just return immediately, especially to avoid side effects of
    # modifying a list being iterated over
    for i, item in enumerate(godotfile):
        if isinstance(item, res_type) and \
           item.name == oldres:
            del godotfile[i]
            return True

    return False

def replace_sub_res(godotfile, newres, oldres):
    return replace_res(godotfile, newres, oldres,
                       sub_resource_re, GodotSubResource, "SubResource(\"{}\")")

def replace_ext_res(godotfile, newres, oldres):
    return replace_res(godotfile, newres, oldres,
                       ext_resource_re, GodotExtResource, "ExtResource(\"{}\")")

def deduplicate(godotfile, sub_dupes_lists, ext_dupes_lists):
    for dupes_list in sub_dupes_lists:
        for dupe in dupes_list[1:]:
            if replace_sub_res(godotfile, dupes_list[0], dupe):
                print(f"Deduplicated sub resource {dupe}")
            else:
                print(f"Couldn't find sub resource {dupe} to deduplicate!")

    for dupes_list in ext_dupes_lists:
        for dupe in dupes_list[1:]:
            if replace_ext_res(godotfile, dupes_list[0], dupe):
                print("Deduplicated ext resource {dupe}")
            else:
                print(f"Couldn't find ext resource {dupe} to deduplicate!")

def find_item_by_ref_name(path_list, name):
    pass

def usage():
    print("USAGE: {sys.argv[0]} <check|list|dedup> <infile> [outfile]")

def load():
    with open(sys.argv[2], 'r') as infile:
        godotfile = read_godot_file(infile)

    return godotfile

def check(godotfile):
    # other operations will need this to populate various fields

    duplicate_ext_names, duplicate_sub_names, missing_ext_resources, missing_sub_resources, missing_nodes = check_file(godotfile)

    path_list = build_paths(godotfile)

    print("Duplicate ext resource names:")
    for res in duplicate_ext_names:
        print(f" Name: {res}")
    print("Duplicate sub resource names:")
    for res in duplicate_sub_names:
        print(f" Name: {res}")
    if len(duplicate_ext_names) != 0 or len(duplicate_sub_names) != 0:
        print("Duplicate resource names might make missing resource names results unreliable.")
    print("Missing ext resources:")
    for res in missing_ext_resources:
        print(f" Name: {res}")
    print("Missing sub resources:")
    for res in missing_sub_resources:
        print(f" Name: {res}")
    print("Nodes with missing parents:")
    for res in missing_nodes:
        print(f" Name: {res}")

    return path_list

def dedup(godotfile, path_list):
    sub_dupes_lists, ext_dupes_lists = find_dupes(godotfile)

    print(f"Sub Resource Duplicates:")
    for dupes_list in sub_dupes_lists:
        print(" Dupe set:")
        for dupe in dupes_list:
            print(f"  Name: {dupe}")
    print(f"Ext Resource Duplicates:")
    for dupes_list in ext_dupes_lists:
        print(" Dupe set:")
        for dupe in dupes_list:
            print(f"  Name: {dupe}")
 
    if len(sys.argv) > 3:
        if sys.argv[3] == sys.argv[2]:
            print("Input and output file are the same!")
        else:
            deduplicate(godotfile, sub_dupes_lists, ext_dupes_lists)

            with open(sys.argv[3], 'w') as outfile:
                for item in godotfile:
                    outfile.write(str(item))
                # this goes at the end
                outfile.write(godotfile[0].str_end())

def list_res(path_list):
    for item in path_list:
        print(item[1])

if __name__ == '__main__':
    if len(sys.argv) >= 2:
        if sys.argv[1] == 'check':
            if len(sys.argv) < 3:
                usage()
                sys.exit()
            godotfile = load()
            _ = check(godotfile)
        elif sys.argv[1] == 'dedup':
            if len(sys.argv) < 3:
                usage()
                sys.exit()
            godotfile = load()
            path_list = check(godotfile)
            dedup(godotfile, path_list)
        elif sys.argv[1] == 'list':
            if len(sys.argv) < 3:
                usage()
                sys.exit()
            godotfile = load()
            path_list = check(godotfile)
            list_res(path_list)
        else:
            usage()
    else:
        usage()
