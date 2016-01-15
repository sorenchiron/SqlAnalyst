#!/usr/bin/env python3
## by sorenchen
##                  Copyright 2015-2016 Soren Chen
##
##    Licensed under the Apache License, Version 2.0 (the "License");
##    you may not use this file except in compliance with the License.
##    You may obtain a copy of the License at
##
##        http://www.apache.org/licenses/LICENSE-2.0
##
##    Unless required by applicable law or agreed to in writing, software
##    distributed under the License is distributed on an "AS IS" BASIS,
##    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##    See the License for the specific language governing permissions and
##    limitations under the License.
##

import os
import glob
import re
import sys


class LogWriter(object):
    """if log filename is given in constructor, the file will be opened automatically, you can use it directly"""
    DefaultWriter = sys.stdout

    def __init__(self,fname=None):
        super(LogWriter, self).__init__()
        self.Verbose = True
        self.DefaultWriter = sys.stdout
        self.Writer = self.DefaultWriter
        self.fname=fname
        if fname is not None:
            self.open(fname)

    def open(self,fname,append=False):
        """close last (non-stdio) logfile then create new. Overwrites old log if append left False"""
        if self.Writer is not self.DefaultWriter:
            self.close()
        if not append:
            self.Writer=open(fname,'w')
        else:
            self.Writer=open(fname,'a+')
        self.fname=fname
        return self

    def log(self, mflag, *mcontent, force=False):
        """you can use any flag like 'warning' 'error' 'running' etc followed with it's description
        e.g.  log('success',15,'tasks','passed','statues good')
        flag will be Uppercase when written into log stream.
        when flag is 'error', upper or lower, the log will be output whatever verbose is set to.
        when force=True is set, this log will also be forced to output
        """
        content = [str(c) for c in mcontent]
        flag = str(mflag)
        if self.Verbose or (flag.lower() == "error") or force:
            self.Writer.write("##" + flag.upper() + "##:" + " ".join(content) + os.linesep)


    def save(self):
        """this write your logs to file without closing it. you can do this anytime in case of failing reaching close().
        this actually save,close and open the stream again"""
        if (self.Writer is not None) and (self.fname is not None):
            self.Writer.close()
            self.Writer=open(self.fname,"a+")

    def set_log_verbose(self, isverbose):
        """mute unnecessary log by set false"""
        self.Verbose = isverbose

    def set_log_writer(self, writer):
        """create an io-stream yourself and pass it in. logs will be output to it."""
        self.Writer = writer

    def close(self):
        """don not worry about stdio closing, this method is safe"""
        if self.Writer is sys.stdout:
            self.log("WARNING", "Not allow to close std out")
        else:
            self.Writer.close()
        self.fname=None



class SqlEntity(LogWriter):
    """this is tree node class,containing all necessary information about a sql file and its structure
    just dir it and help(SqlEntity.method)
    """
    def __init__(self, filename, creates, deps):
        super(SqlEntity, self).__init__()
        self.FileName = filename
        self.Creates = creates  # I create these tables
        self.Deps = deps  # I need them to be done first (db name ,table name)
        self.DepFileEntities = []  # I need these tables
        self.SubRoutineEntities = []  # they need me
        self.InternalDeps = []  # for my own usage
        self.MissingDeps = []  # nobody creates that , I myself didn't create it neither !
        self.IntactDepTables = []
        self.Complete = True

    def __bound_relation__(self, entity_list):
        """each pair of nodes should only bound once"""
        dep_tables = [db_table[1] for db_table in self.Deps]
        for entity in entity_list:
            if self is entity:
                continue
            self.log("LOG", "Comparing:", self.FileName, 'with', entity.FileName)  ########################LOG
            should_depend = False
            should_gen = False
            if entity not in self.DepFileEntities:  ## do i depend on it?
                for c in entity.Creates:
                    if c in dep_tables:
                        should_depend = True
                        self.log("log", self.FileName, "requires", entity.FileName, "to provide table:", c)
                        if c in self.IntactDepTables:
                            self.log("error", "Duplicate Table", c, "created by", entity.FileName)
                        else:
                            self.IntactDepTables.append(c)
            if entity not in self.SubRoutineEntities:  ## is it my son ?
                for d in entity.Deps:
                    if d[1] in self.Creates:
                        should_gen = True
                        entity.IntactDepTables.append(d[1])  ## my son's table has a source from me
                        self.log("log", self.FileName, "is a father of", entity.FileName, "by providing table:", d[1])
            if should_gen and should_depend:
                self.log("error", "Loop Depend:", self.FileName, entity.FileName)
            if should_depend:  ## i depend on it
                self.DepFileEntities.append(entity)
                entity.SubRoutineEntities.append(self)
            if should_gen:  ## it's my son
                self.SubRoutineEntities.append(entity)
                entity.DepFileEntities.append(self)
        self.InternalDeps = [d[1] for d in self.Deps if d[1] not in self.IntactDepTables]
        self.MissingDeps = [d for d in self.InternalDeps if d not in self.Creates]
        self.MissingDeps = sorted(self.MissingDeps, key=len, reverse=True)
        ## append database prefix for missing deps
        missing_deps = []
        for md in self.MissingDeps:
            formated_md=md
            for dep in self.Deps:
                if md == dep[1] and len(dep[0])>0:
                    formated_md = dep[0]+"::"+dep[1]
                    break
            missing_deps.append(formated_md)
        self.MissingDeps = missing_deps


    def check_complete(self, missing_deps):
        """given a list of confirmed missing dependencies,
        complete is defined as: None of its deps is claimed as Missing,it can run."""
        if not self.Complete:
            return False
        is_complete = True
        for md in missing_deps:
            is_complete = is_complete and (md not in self.MissingDeps)
        for dep in self.DepFileEntities:
            is_complete = is_complete and dep.Complete
        self.Complete = is_complete
        return is_complete

    def gen_drops(self):
        return [ ("drop table %s ;" % tname) for tname in self.Creates]

    def is_final_task(self):
        """if it should run at last"""
        return len(self.SubRoutineEntities) == 0

    def is_base_task(self):
        """if it should run first"""
        return len(self.DepFileEntities) == 0
        ##len(self.InternalDeps)

    def is_obsolete_task(self):
        """ordinary tree has only one node"""
        return self.is_base_task() and self.is_final_task()

    def type(self):
        """show type of this task"""
        if self.is_obsolete_task():
            print("Obsolete")
        elif self.is_final_task():
            print("Final")
        elif self.is_base_task():
            print("Base")
        else:
            print("Mid")

    def show_stack_tree(self):
        """deep traverse, show all job chains in stack"""
        upper_stack = [self]
        next_stack = []
        depth = 1
        print("Layer 0 is the final task")
        while len(upper_stack) > 0:
            print("=======Layer%d start=======" % depth)
            for entity in upper_stack:
                print(entity.FileName)
                next_stack.extend(entity.DepFileEntities)
            upper_stack = list(set(next_stack))
            next_stack.clear()
            depth = depth + 1
        print("========Leaf Tasks========")

    def __depthTraverse__(self, depth=0):
        prefix = ""
        if depth == 0:
            prefix = '*'
        output = prefix + "\t |" * depth + " " + self.FileName
        print(output)
        for e in self.DepFileEntities:
            e.__depthTraverse__(depth + 1)

    def find_table(self, table):
        """in which sql file this table is created"""
        Found = False
        if table in self.Creates:
            print("Table found in", self.FileName)
            Found = True
        for e in self.DepFileEntities:
            Found = Found or e.find_table(table)
        return Found

    def show_list_tree(self):
        """water fall style tree"""
        self.__depthTraverse__()

    def show_tree(self):
        """using this node as root, ignore its fathers"""
        self.show_list_tree()

    def show(self):
        """detail information of this sql"""
        print("Filename:", self.FileName)
        print("Creates:", "\n".join(self.Creates))
        print("Uses:", "\n".join([d[0] + d[1] for d in self.Deps if d[1] not in self.InternalDeps]))
        print("Missing:", "\n".join(self.MissingDeps))


###########################
###########################

class SqlAnalyst(LogWriter):
    """this module is a tool for analyzing the consanguinity and relation of
sql source files, it can locate table creation and select usage in every file,
then build dependency trees. the result is usually a forest.
generically, the forest is for using as an execution-order procedure.
by using this tool, you will be able to handle whatever messy SQL jobs
without having to know every line of code.

command line simplest usage:
 >cd sql_dir
 >sqla                              #automatic, simple and smart

 >sqla -f education_info_table      #to find where that table is created
 >sqla -d -m                        #don't show the tree, just tell me what source tables are missing!
 >sqla -i a.sql                     #tell me what this sql-file creates/uses/missing

coding usage:
0 from sqla import SqlAnalyst
1 sa = SqlAnalyst.SqlAnalyst()
2 sa.run("d:/works/sqls/sqljob_1")
3 sa.show()"""
    DefaultSearchPattern = "*.sql"

    def __init__(self, encoding="utf-8", ):
        super(SqlAnalyst, self).__init__()
        self.EntityList = []
        self.FileNames = []
        self.encoding = encoding
        self.RootEntities = []
        self.BaseEntities = []
        self.MissingTables = []
        self.DefaultEncoding = encoding
        # command arguments
        self.SearchPattern = self.DefaultSearchPattern

    def run(self, tardir="."):
        """if the folder containing sqls is not explicitly given,
        this scans the current working directory
        use os.getcwd() and os.chdir() to know more about your position.

        since sqla can not reach your database interface,
        run() assumes all missing tables exists in your database,and set all nodes as 'complete'
        you can provide a missing-list to __calculate_incomplete() method, after run().
        if missing list is provided, show() will filter incomplete trees by default.
        """
        cur_dir = os.getcwd()
        for filename in self.__scan__(tardir):
            (c, d) = self.__discover_dep__(filename)
            a = SqlEntity(filename, c, d)
            a.set_log_verbose(self.Verbose)
            self.EntityList.append(a)
        self.__build_forest__()
        self.__calculate_roots__()
        self.__calculate_bases__()
        self.__calculate_missing__()
        os.chdir(cur_dir)
        self.log("Done")

    def show(self, block_incomplete=True):
        """after analyzing, use this to show the default-style forest
        by default, all nodes are initialized as 'complete', hence all trees will be shown.
        but if you provided a missing list to __calculate_incomplete() after run(),
        the block_incomplete=True will hide those invalid trees that has missing deps.
        """
        total_trees = len(self.RootEntities)
        failure_trees = len([e for e in self.RootEntities if not e.Complete])
        print("There are", total_trees, "trees in total,in which",failure_trees,"trees failed")
        print("showing",total_trees-failure_trees,"trees")
        print("Each tree's Root is marked by \'*\'")
        for e in self.RootEntities:
            if block_incomplete and (not e.Complete):
                continue
            e.show_tree()

    def find(self, table):
        """return sql file-name of its creation"""
        Found = False
        for e in self.RootEntities:
            Found = Found or e.find_table(table)
        if not Found:
            print("Table Not Found")

    def show_roots(self):
        """show all top level tasks information"""
        sum = 0
        print("following SQL should be executed At Last")
        for entity in self.RootEntities:
            print('[', sum, ']', entity.FileName)
            sum = sum + 1
        print("Final Tasks:", sum)

    def show_leaves(self):
        """show all bottom level tasks information"""
        sum = 0
        print("following SQL can be executed Firstly safely")
        for entity in self.BaseEntities:
            print('[', sum, ']', entity.FileName)
            sum = sum + 1
        print("Base Tasks:", sum)

    def show_info(self, fname):
        """show deps/creates/missing of a sql-file"""
        found = False
        for e in self.EntityList:
            if fname == e.FileName:
                e.show()
                found = True
                break
        if not found:
            print("file not found")

    def show_missing(self):
        """all the missing tables under the directory"""

        for tname in self.MissingTables:
            self.log("missing", tname, force=True)

    def show_by_root_no(self, No):
        """using the index number printed by show_roots()
        this function shows one tree lead by that root task
        """
        if No < 0 or (No + 1) > len(self.RootEntities):
            print("invalid index number")
            return
        self.RootEntities[No].show_tree()

    def show_by_leaf_no(self, leaf_no):
        pass
        # base = self.BaseEntities[leaf_no]
        # TODO::

    def show_failure_files(self):
        """show the key (bottle-neck) files that cause incompeletion
        which means, those sql-files are not complete, trees go through these files became invalid to execute"""
        for e in self.EntityList:
            dep_success = True
            for dep in e.DepFileEntities:
                dep_success = dep_success and dep.Complete
            if (not e.Complete) and dep_success:
                e.show()

    def useutf8(self):
        self.encoding = "utf-8"

    def usegbk(self):
        self.encoding = "gb2312"

    def usedefault_encoding(self):
        """default is utf-8"""
        self.encoding = self.DefaultEncoding

    def assign_encoding(self, encoding):
        """require a string, like 'gb2221','unicode' """
        self.encoding = encoding

    def get_root_entities(self):
        """return SqlEntity instance list of root nodes"""
        return self.RootEntities

    def reset(self):
        """you must reset before run again"""
        self.EntityList = []
        self.FileNames = []
        self.RootEntities = []
        self.BaseEntities = []

    def gen_utils(self):
        pass
        ## TODO::

    def gen_drop_all(self):
        """generate sql statements for dropping all created tables"""
        for e in self.EntityList:
            for ct in e.gen_drops():
                print(ct)

    def gen_drop_mid(self):
        """generate sql statements for dropping all tables except the final ones
the final ones are left for use."""
        for e in self.EntityList:
            if e.is_final_task:
                continue
            for ct in e.gen_drops():
                print(ct)

    def set_search_pattern(self,pattern):
        self.SearchPattern = pattern

    def __scan__(self, tardir):
        os.chdir(tardir)
        FileNames = []
        for fname in glob.glob(self.SearchPattern.lower()):
            FileNames.append(fname)
        for fname in glob.glob(self.SearchPattern.upper()):
            FileNames.append(fname)
        FileNames = list(set(FileNames))
        self.FileNames = FileNames
        if len(FileNames)==0:
            self.log("warning","no file found under pattern",self.SearchPattern.lower(),"or",self.SearchPattern.upper())
        return FileNames

    def __remove_comment__(self):
        # TODO
        pass

    def __discover_dep__(self, filename):
        fstr = None
        try:
            self.useutf8()
            fstr = open(filename, 'r', encoding=self.encoding).read().lower()
        except:
            self.usegbk()
            fstr = open(filename, 'r', encoding=self.encoding).read().lower()
        else:
            pass
        create_pattern2 = """(?:create\s+table\s+(?:if\s+not\s+exists\s+)?)(\w+)"""
        creates = [t for t in re.findall(create_pattern2, fstr)]
        ##       dep_pattern1="""(?:from\s+)(\w+\s*\:\s*\:)?(?:\s*)(\w+)"""
        ##       dep_pattern2="""(?:join\s+)(\w+\s*\:\s*\:)?(?:\s*)(\w+)(?:\s+\w+)?(?:\s+on)"""
        dep_pattern = """(?:(?:from|join)\s+)(?:(\w+)(?:\s*\:\s*\:))?(?:\s*)(\w+)"""
        deps = [t for t in re.findall(dep_pattern, fstr)]
        return (creates, deps)

    def __build_forest__(self):
        iters = len(self.EntityList) - 1
        EntityList = self.EntityList.copy()
        for i in range(iters):
            entity = EntityList.pop()
            entity.__bound_relation__(EntityList)

    def __calculate_roots__(self):
        self.RootEntities = [e for e in self.EntityList if e.is_final_task()]
        return self.RootEntities

    def __calculate_bases__(self):
        self.BaseEntities = [e for e in self.EntityList if e.is_base_task()]
        return self.BaseEntities

    def __calculate_missing__(self):
        missing_tables = []
        for e in self.EntityList:
            missing_tables.extend(e.MissingDeps)
        self.MissingTables = sorted(list(set(missing_tables)), key=len, reverse=True)

    def __calculate_incomplete__(self, missing_deps):
        is_updated = True
        while is_updated:
            is_updated = False
            for e in self.EntityList:
                last_status = e.Complete
                is_updated = is_updated or (last_status != e.check_complete(missing_deps))


#####################################
version = '''1.3.3'''
#####################################
require_argument = True
no_argument = False
no_doc = None
no_abbr = None
arg_is_set = True
arg_not_set = False
arg_val = None
arg_type_fullname = 1
arg_type_abbr = 2
arg_type_value = -1

default_dir = "."


def __tell_arg_type__(arg):
    m = re.match("^\-\-(\w+)", arg)
    if m is not None:
        return (arg_type_fullname, m.groups()[0])
    m = re.match("^\-(\w+)", arg)
    if m is not None:
        return (arg_type_abbr, m.groups()[0])
    return (arg_type_value, arg)


def __locate_arg_no__(flag_type, flag, arg_map, arg_index):
    query_name = ""
    if flag_type == arg_type_fullname:
        query_name = "full name"
    elif flag_type == arg_type_abbr:
        query_name = "abbreviation"
    i = 0
    for arg_info in arg_map:
        if arg_info[arg_index[query_name]] == flag:
            return i
        i += 1
    return 0

def __format_help_doc__(arg_item, arg_index):
    if arg_item[arg_index["doc"]] is not no_doc:
            abbr = arg_item[arg_index["abbreviation"]]
            arg = arg_item[arg_index["has argument"]]

            if abbr is no_abbr:
                abbr = "  "
            else:
                abbr = '-'+abbr

            if arg is no_argument:
                arg = ""
            else:
                arg = "one arg,"

            doc = "--%s %s\t:%s %s" % (arg_item[arg_index["full name"]],abbr,arg,arg_item[arg_index["doc"]])
            return doc
    return no_doc

def __help_bad_arg__(bad_arg, arg_map, arg_index):
    help_result = []
    for arg_item in arg_map:
        if (bad_arg in arg_item[arg_index["full name"]] or
        (arg_item[arg_index["abbreviation"]] is not no_abbr and
            bad_arg in arg_item[arg_index["abbreviation"]] ) or
        ( arg_item[arg_index["doc"]] is not no_doc and
            bad_arg in arg_item[arg_index["doc"]] )
        ):
            help_result.append(__format_help_doc__(arg_item, arg_index))
    return help_result




def __none__(sa, *args):
    print("not implemented")


def __bad_arg__(sa, arg_map, arg_index, value):
    print("bad arguments:", value)
    print("please use help to see the usage")
    exit(0)


def __arg_f__(sa, arg_map, arg_index, value):
    sa.find(value)


def __arg_v__(sa, arg_map, arg_index):
    sa.set_log_verbose(True)


def __arg_t__(sa, arg_map, arg_index, value):
    global default_dir
    default_dir = value

def __arg_s__(sa, arg_map, arg_index, value):
    sa.set_search_pattern(value)

def __help__(sa, arg_map, arg_index):
    print(SqlAnalyst.__doc__)
    for info in arg_map:
        doc = __format_help_doc__(info, arg_index)
        if doc is not no_doc:
            print(doc)
    exit(0)


def __arg_d__(sa, arg_map, arg_index):
    pass


def __run__(sa, arg_map, arg_index):
    sa.run(default_dir)


def __arg_b__(sa, arg_map, arg_index, value):
    missing_deps = [line.lstrip().rstrip() for line in open(value, 'r')]
    sa.__calculate_incomplete__(missing_deps)

def __arg_g__(sa, arg_map, arg_index, value):
    if value == "drop-all":
        sa.gen_drop_all()
        exit()
    elif value == "drop-mid":
        sa.gen_drop_mid()
        exit()
    elif os.path.isfile(value):
        for e in sa.EntityList:
            if e.FileName == value :
                for d in e.gen_drops():
                    print (d)
                exit(0)
    print ("gen: no such option or filename",value)
    exit(0)

def __show__(sa, arg_map, arg_index):
    if not arg_map[__locate_arg_no__(arg_type_fullname, "dry-run", arg_map, arg_index)][arg_index["argument set"]]:
        sa.show()


def __arg_m__(sa, arg_map, arg_index):
    sa.show_missing()


def __arg_i__(sa, arg_map, arg_index, value):
    sa.show_info(value)


__arg_map__ = [
    ["version",no_abbr,__none__,no_argument,arg_not_set,arg_val,"sqla, version "+version+" by sorenchen. copyright 2015-2016"],
    ["bad arg", no_abbr, __bad_arg__, no_argument, arg_not_set, arg_val,no_doc],
    ["verbose", 'v', __arg_v__, no_argument, arg_not_set, arg_val,"show processing logs or not"],
    ["target-dir", 't', __arg_t__, require_argument, arg_not_set, arg_val,"dir should not end with \\ or /"],
    ["search-pattern",'s',__arg_s__, require_argument, arg_not_set, arg_val,"default *.sql/SQL. you can use *.* and so on"],
    ["encoding", 'e', __none__, require_argument, arg_not_set, arg_val,no_doc],  # TODO:: set encoding
    ["help", 'h', __help__, no_argument, arg_not_set, arg_val,"show help information"],  # TODO:: show help
    ["dry-run", 'd', __arg_d__, no_argument, arg_not_set, arg_val,"run but don't show, should be followed by other \n\t\tcommands if you want see something come out"],  # don't show[]
    ## run stage
    ["run", no_abbr, __run__, no_argument, arg_is_set, arg_val,no_doc],  # This is the RUN[] stage
    ["block-incomplete", 'b', __arg_b__, require_argument, arg_not_set, arg_val,"don't show incomplete branch that really \n\t\tmissing deps, given a file containing confirmed missing table, \n\t\tone table-name each line, No database prefix."],
    ["generate",'g',__arg_g__, require_argument, arg_not_set, arg_val,"generate utils for sql maintenance,\n\t\taccept param: drop-all | drop-mid | filename"],
    # don't show the branch tha cannot run
    ["show", no_abbr, __show__, no_argument, arg_is_set, arg_val,no_doc],
    ## run over
    ["missing", 'm', __arg_m__, no_argument, arg_not_set, arg_val,"show missing tables that are not \n\t\tcreated by any file, but are used"],  #
    ["info", 'i', __arg_i__, require_argument, arg_not_set, arg_val,"show deps/creats/missing of a .sql file,\n\t\ta filename is required"],  # show deps and gens of a .sql
    ["find", 'f', __arg_f__, require_argument, arg_not_set, arg_val,"given a table name, find where it is created"]  # find create table in sql files
]

__arg_index__ = {"full name": 0, "abbreviation": 1, "function": 2, "has argument": 3, "argument set": 4,
                 "argument value": 5,"doc":6}


def __resolve_arguments__(args, arg_map, arg_index):
    total = len(args)
    dealing = 0
    while dealing <= total - 1:
        (arg_type, value) = __tell_arg_type__(args[dealing])
        if arg_type < 0:
            print ("sqla: bad argument input at:",value)
            help_result = __help_bad_arg__(value,arg_map,arg_index)
            if len(help_result)>0:
                print ("sqla assuming you want these:")
                for h in help_result:
                    print (h)
            exit()
        no = __locate_arg_no__(arg_type, value, arg_map, arg_index)
        if arg_map[no][arg_index["has argument"]]:
            if dealing + 1 >= total or __tell_arg_type__(args[dealing + 1])[
                0] > 0:  # if no further args given OR  type is flag or abbr flag
                print("sqla: flag", value, "requires one argument, none given")
                exit(0)
            dealing += 1
            arg_map[no][arg_index["argument value"]] = args[dealing]
        arg_map[no][arg_index["argument set"]] = True
        dealing += 1


def __exec__(sa, arg_map, arg_index):
    for arg in arg_map:
        if arg[arg_index["argument set"]]:
            if arg[arg_index["has argument"]]:
                arg[arg_index["function"]](sa, arg_map, arg_index, arg[arg_index["argument value"]])
            else:
                arg[arg_index["function"]](sa, arg_map, arg_index)


if __name__ == "__main__":
    sa = SqlAnalyst()
    sa.set_log_verbose(False)

    if len(sys.argv) > 1:
        args = sys.argv[1:]
        __resolve_arguments__(args, __arg_map__, __arg_index__)
    __exec__(sa, __arg_map__, __arg_index__)
