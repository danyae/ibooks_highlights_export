#!/usr/bin/env python
# -*- coding: utf-8 -*-

from jinja2 import Environment, FileSystemLoader
from glob import glob
import os
import sqlite3
import datetime
import re
import sys
if sys.version_info < (3, 0):
    # Python 2
    import Tkinter as tk
else:
    # Python 3
    import tkinter as tk
import tkMessageBox
import tkFileDialog

PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_ENVIRONMENT = Environment(
    autoescape=False,
    loader=FileSystemLoader(os.path.join(PATH, 'templates')),
    trim_blocks=False)


def get_all_titles():
    global cur2
    res = cur2.execute("select ZASSETID, ZTITLE, ZAUTHOR from ZBKLIBRARYASSET;").fetchall()
    m = {}
    for r in res:
        m[r[0]] = {"ZTITLE": r[1], "ZAUTHOR": r[2]}

    return m


def get_all_relevant_assetids_and_counts():
    global cur1
    q = "select count(*), ZANNOTATIONASSETID from ZAEANNOTATION where ZANNOTATIONREPRESENTATIVETEXT " \
        "IS NOT NULL group by ZANNOTATIONASSETID;"
    res = cur1.execute(q).fetchall()
    return res

def get_all_relevant_titles():
    aids_and_counts = get_all_relevant_assetids_and_counts()
    print aids_and_counts
    all_titles = get_all_titles()

    op = {}

    for cnt, aid in aids_and_counts:
        all_titles[aid]["COUNT"] = cnt
        op[aid] = all_titles[aid]

    return op

def bold_text(selected_text, representative_text):
    left = representative_text.find(selected_text)
    right = left + len(selected_text)

    op = representative_text[:left] + "<b>" +  representative_text[left:right] + "</b>" + representative_text[right:]
    return op

def get_book_details(assetid):
    global cur2
    res2 = cur2.execute("select ZTITLE, ZAUTHOR from ZBKLIBRARYASSET where ZASSETID=?", (assetid,))
    t =  res2.fetchone()
    return t[0] + ", " + t[1]

def get_all_highlights():
    global cur1
    res1 = cur1.execute("select ZANNOTATIONASSETID, ZANNOTATIONREPRESENTATIVETEXT, ZANNOTATIONSELECTEDTEXT, "
                        " ZANNOTATIONSTYLE from ZAEANNOTATION order by ZANNOTATIONASSETID, ZPLLOCATIONRANGESTART;")

    return res1

def get_chapter_name():
    global cur1
    res1 = cur1.execute("select ZANNOTATIONASSETID, ZANNOTATIONREPRESENTATIVETEXT, ZANNOTATIONSELECTEDTEXT, "
                        " ZANNOTATIONSTYLE, ZFUTUREPROOFING5 from ZAEANNOTATION "
                        "order by ZANNOTATIONASSETID, ZPLLOCATIONRANGESTART ;")
    t =  res1.fetchone()
    return t[4]

def make_text_readable(text, every=80):
    text = text.replace('\n',' ').replace('"','').replace("&","and")
    return ''.join(text[i:i+every] for i in xrange(0, len(text), every))


def get_asset_title_tab():
    global cur2

    res2 = cur2.execute("select distinct(ZASSETID), ZTITLE, ZAUTHOR from ZBKLIBRARYASSET")
    for assetid, title, author in res2:
        asset_title_tab[assetid] = [title, author]

    return asset_title_tab


def get_color(num):
    if num == 0:
        return "b_gray"
    elif num == 1:
        return "b_green"
    elif num == 2:
        return "b_blue"
    elif num == 3:
        return "b_yellow"
    elif num == 4:
        return "b_pink"
    elif num == 5:
        return "b_violet"
    else:
        return "b_gray"

def get_mm_color (num):
    if num>7:
        return ((num - 2) % 6) + 2
    else:
        return num

def get_mind_map_contents(book_id):
    res1 = cur1.execute("select distinct(ZFUTUREPROOFING5) from ZAEANNOTATION "
                    "where (ZANNOTATIONSELECTEDTEXT not NULL)  AND  `ZANNOTATIONASSETID` = '"+str(book_id)+"' order by"
                    " ZANNOTATIONASSETID, ZPLLOCATIONRANGESTART ;")
    chapters = []
    for chapter in res1:
        if chapter not in chapters:
            chapters.append(chapter[0])
    print chapters


    chapters_list = []
    counter = 1
    for ch in chapters:
        chapters_list.append([ch,chapters.index(ch)+1, counter])
        counter += 1


    res1 = cur1.execute("select ZANNOTATIONASSETID, ZANNOTATIONREPRESENTATIVETEXT, ZANNOTATIONSELECTEDTEXT, "
                    "ZFUTUREPROOFING5, ZANNOTATIONSTYLE, ZFUTUREPROOFING5 from ZAEANNOTATION "
                    "where (ZANNOTATIONSELECTEDTEXT not NULL)  AND  `ZANNOTATIONASSETID` = '"+str(book_id)+"' order by"
                    " ZANNOTATIONASSETID, ZPLLOCATIONRANGESTART ;")


    annotations = []
    for ZANNOTATIONASSETID, ZANNOTATIONREPRESENTATIVETEXT, ZANNOTATIONSELECTEDTEXT, \
        ZFUTUREPROOFING5, ZANNOTATIONSTYLE, ZFUTUREPROOFING5 in res1:
        annotations.append([ZANNOTATIONASSETID, ZANNOTATIONREPRESENTATIVETEXT, ZANNOTATIONSELECTEDTEXT,
        ZFUTUREPROOFING5, ZANNOTATIONSTYLE, chapters.index(ZFUTUREPROOFING5) + 1, counter])
        counter += 1

    # beginning another way of doing the same thing, just more efficient
    res2 = cur2.execute("select distinct(ZASSETID), ZTITLE, ZAUTHOR from ZBKLIBRARYASSET")
    for assetid, title, author in res2:
        asset_title_tab[assetid] = [assetid, title, author]

    today = datetime.date.isoformat(datetime.date.today())
    print get_book_details(book_id)
    print book_id


    template = TEMPLATE_ENVIRONMENT.get_template("open_mindmap.xml")

    template.globals['get_mm_color'] = get_mm_color
    template.globals['make_text_readable'] = make_text_readable
    template.globals['get_book_details'] = get_book_details


    #Move annotations to chapter object
    chapters = {}
    nodes = []
    annotations_counter = 0
    fake_chapter_counter = 1
    if len(chapters_list) != 1:
        for ch in chapters_list:
            chapters[ch[0]] = [] 
    else:
        # Split everything in 5 parts
        chapters = {"Part " + str(number+1): [] for number in range(5)}
        annotations_per_fake_chapter = len(annotations) / 5

    
    for ann in annotations:
        content = ann[1]
        if (content == None):
            content = ann[2]
            
        if len(chapters_list) != 1:
            chapters[ann[3]].append(content)
        else:
            if (annotations_counter < annotations_per_fake_chapter):
                fake_chapter_name = "Part " + str(fake_chapter_counter)
                chapters[fake_chapter_name].append(content)
                annotations_counter += 1
            else:
                fake_chapter_counter += 1
                annotations_counter = 0

    for k in chapters.keys():
        print (">>>", k)
        try:
            chapter_name = k
            if k == "" or k == None:
                chapter_name = "Misc"
            nodes.append ([chapter_name, chapters[k]])
            print chapter_name
            print chapters[k][0]
            print "\n"
        except TypeError, NameError:
            print ("error",k, len(chapters[k]))
        
    smmx = template.render(obj={"last":"###", "date":today,
        "assetlist":asset_title_tab, "book_name": get_book_details(book_id),
            "chapters": nodes})

    return smmx.encode('utf-8')

def file_save(book_id):
    f = tkFileDialog.asksaveasfile(mode='w', defaultextension=".opml")
    if f is None: # asksaveasfile return `None` if dialog closed with "cancel".
        return
    mind_map_content = get_mind_map_contents(book_id)
    print(book_id)
    f.write(mind_map_content)
    f.close() 


if __name__ == "__main__":

    asset_title_tab = {}
    base1 = "~/Library/Containers/com.apple.iBooksX/Data/Documents/AEAnnotation/"
    base1 = os.path.expanduser(base1)
    sqlite_file = glob(base1 + "*.sqlite")

    if not sqlite_file:
        print "Couldn't find the iBooks database. Exiting."
        exit()
    else:
        sqlite_file = sqlite_file[0]

    base2 = "~/Library/Containers/com.apple.iBooksX/Data/Documents/BKLibrary/"
    base2 = os.path.expanduser(base2)
    assets_file = glob(base2 + "*.sqlite")

    if not assets_file:
        print "Couldn't find the iBooks assets database. Exiting."
        exit()
    else:
        assets_file = assets_file[0]

    db1 = sqlite3.connect(sqlite_file, check_same_thread=False)
    cur1 = db1.cursor()

    db2 = sqlite3.connect(assets_file, check_same_thread=False)
    cur2 = db2.cursor()




    #only prints a list of books with highlights and exists
    res2 = cur2.execute("select distinct(ZASSETID), ZTITLE, ZAUTHOR from ZBKLIBRARYASSET")


    counter = 1
    books_list = []
    for assetid, title, author in res2:
        books_list.append((counter, assetid, unicode(title)+"\t"+unicode(author)))
        counter += 1

    def Get(event):    
        l = event.widget
        sel = l.curselection()
        if len(sel) == 1:
            s = l.get(sel[0])
            book_id = books_list[sel[0]][1]
            print (s)
            print books_list[sel[0]][1], books_list[sel[0]][2]
            if s[0] == '-':
                l.selection_clear(sel[0])
            else:
                file_save(book_id)


    top = tk.Tk()


    Lb1 = tk.Listbox(top, height=20, width=50, selectmode = tk.SINGLE)
    Lb1.grid(row=0, column=0, sticky=tk.N+tk.S+tk.E+tk.W)
    for book in books_list:
        Lb1.insert(book[0], book[2])
        print(book[0], book[1])
        print(unicode(book[2]))
        print("\n\n")

    Lb1.pack()
    Lb1.bind("<<ListboxSelect>>", Get)
    top.mainloop()
