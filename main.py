import json
import os
import sys
import datetime
from unicodedata import name
import v8profilerspecfication as v8p
from treelib import Tree, Node
import copy

def diffequalTreePattern(tree1,tree2):
    t1list = [i.tag for i in tree1.all_nodes()]
    t2list = [i.tag for i in tree2.all_nodes()]
    t1list.sort()
    t2list.sort()
    return  t1list == t2list
        
# cluster args pattern
def getArgPattern(arg_field,layername):
    """
    return Treeobj
    """
    tree = Tree()
    tree.create_node(tag=layername,identifier=layername, data=type(arg_field))
    if type(arg_field) == list and len(arg_field)>=1:
        sametypeIndicator = type(arg_field[0])
        sametypeFlag = True
        for i in arg_field:
            if type(i) != sametypeIndicator:
                sametypeFlag=False
        if sametypeFlag == True:
            if sametypeIndicator is not dict and sametypeIndicator is not list:
                tagname = f"{layername}-{str(sametypeIndicator)}"
                tree.create_node(tag=tagname,identifier=tagname, data=sametypeIndicator,parent=layername)
                return tree
            else:
                if sametypeIndicator is dict:
                    publicset = set()
                    for idx,eachcontent in enumerate(arg_field):
                        publicset.update(eachcontent.keys())
                    subdictnamelist = list(publicset)
                    subdictnamelist.sort()
                    for i in subdictnamelist:
                        tree.create_node(tag=i,identifier=i, data="inlist",parent=layername)
                if sametypeIndicator is list:
                    tagname = f"{layername}-{str(sametypeIndicator)}"
                    tree.create_node(tag=tagname,identifier=tagname, data=sametypeIndicator,parent=layername)
                    return tree
                # tree_merged = copy.deepcopy(tree)
                # for idx,eachcontent in enumerate(arg_field):
                #    duplitree = copy.deepcopy(tree)
                #    duplitree.paste(layername, getArgPattern(eachcontent,idx))
                
        else:
            raise NotImplementedError(f"list {layername} type not same")
        return tree
    elif type(arg_field) == dict and len(arg_field.keys())>=1:
        for key in arg_field.keys():
            treeobj = getArgPattern(arg_field[key],f"{layername}-{key}")
            if treeobj is not None: 
                tree.paste(layername, treeobj)
        return tree
    else:  # not list and dict
        return tree

if __name__ == "__main__":
    name_dict = {}
    cat_dict = {}
    arg_dict = {getArgPattern({},'args'):0}
    profile_file = json.load(open("./259+38427.json"))# ./Profile-20220227T164144.json
    parsedlist = []
    for idx,line in enumerate(profile_file):
        line["ph"] = v8p.Phases(line["ph"])
        try:
            parsedcontent = v8p.phasesToEvents(line["ph"])(**line)
        except Exception as e:
            print(e)
            
        parsedlist.append(parsedcontent)
        if line["name"] not in name_dict.keys(): name_dict[line["name"]] = 0
        name_dict[line["name"]] += 1
        
        if line["cat"] not in cat_dict.keys(): cat_dict[line["cat"]] = 0
        cat_dict[line["cat"]] += 1
        
        argtree = getArgPattern(line['args'],'args')
        
        flaghaveEqual = False
        for key in arg_dict.keys():
            if diffequalTreePattern(argtree,key):
                arg_dict[key] += 1
                flaghaveEqual = True
                break
        if flaghaveEqual==False:
            arg_dict[argtree] = 1
        

    # print functions
    for tree,num in arg_dict.items():
        print(f"totol number {num}")
        tree.show() 
        for node in tree.all_nodes_itr():
            print(node)
        print("======================================================")

    print(name_dict)
    print(cat_dict)