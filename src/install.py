#!/usr/bin/env python3
## by sorenchen
## 2015 10
import os
import shutil
import sys

main_py="SqlAnalyst.py"
## always good for windows
win_path="""C:\\Windows\\System32"""
## in case that /usr/bin is not permited
unix_path="""\\usr\\local\\bin"""
used_path=""
target="sqla.py"

libpath=sys.prefix+'\\'+'Lib'
module="sqla"

print ("preparing Lib installation to:",libpath)

if os.path.exists(win_path):
    print ("windows detected")
    used_path = win_path
elif os.path.exists(unix_path):
    print ("unix-like system detected")
    used_path = unix_path
else:
    print ("permission denied for both",win_path,"and",unix_path)
    print ("abort installation")
    exit(0)

print ("preparing Bin installation to:",used_path)

def has_prev_version(path,target,for_dir=False):
    files=[]
    dirs=[]
    for r,d,f in os.walk(path):
        files=f
        dirs=d
        break
    if for_dir:
        return (target in dirs)
    if not for_dir:
        return (target in files)



if has_prev_version(used_path,target,False):
    print("removing old version")
    os.remove(used_path+"\\"+target)

if has_prev_version(libpath,module,True):
    print("removing old library")
    shutil.rmtree(libpath+"\\"+module)


print ("installing")
try:
    shutil.copyfile(main_py,used_path+"\\"+target)
    os.mkdir(libpath+"\\"+module)
    shutil.copyfile(main_py,libpath+"\\"+module+"\\"+main_py)
except:
    print("something went wrong, please copy it manually")
else:
    print("install succeeded")
rub=input("press any key to proceed")
