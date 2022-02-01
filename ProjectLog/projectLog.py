#!/usr/bin/env python3

import logging
import logging.handlers
import sys
import tkinter as tk
from pathlib import Path
from typing import Dict, Optional

import appdirs

import ProjectLog
from ProjectLog.config import Config
from ProjectLog.firebase import TaskLog
from ProjectLog.ui.dialog import AddProjectDialog, AddTaskDialog
from ProjectLog.ui.project_list import ProjectListviewer
from ProjectLog.ui.task_list import TaskListViewer

MAJOR_VERSION = 0
MINOR_VERSION = 0
BUILD_NUMBER = 1
BRANCH = "NH0"







class ProjectLogApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.__log = logging.getLogger('ProjectLog.ProjectLog')
        self.__log.info("created")
        self.__menuBar: Optional[tk.Menu] = None
        self.__taskListFrame: Optional[TaskListViewer] = None
        self.__projectListFrame: Optional[ProjectListviewer] = None
        self.__core = TaskLog()
        self.__core.authenticate(
            username=Config.instance().email,
            password=Config.instance().password)

        self.title(f"Project Task Tracker v{ProjectLog.__version__}")
        self.__createWidgets()
        self.__createMenu()
        self.protocol('WM_DELETE_WINDOW', self.__deleteWindowHandler)

    def __deleteWindowHandler(self):
        self.__core.close()
        self.destroy()

    def __createWidgets(self):
        self.grid_columnconfigure(0, weight=1, pad=5)
        self.grid_columnconfigure(1, pad=5)
        self.grid_rowconfigure(0, weight=1)
        self.__taskListFrame = TaskListViewer(self, self.__core)
        self.__taskListFrame.grid(row=0, column=0, sticky='new')
        self.__projectListFrame = ProjectListviewer(self, self.__core)
        self.__projectListFrame.grid(row=0, column=1, sticky='new')

    def __createMenu(self):
        if self.__menuBar is not None:
            self.__menuBar.destroy()
        filemenu = tk.Menu(self.__menuBar, tearoff=0)
        filemenu.add_command(label='Add Project', command=self.__addProject)
        filemenu.add_command(label='Add Task', command=self.__addTask)
        filemenu.add_command(label='Remove Project',
                             command=self.__projectListFrame.removeProject)
        filemenu.add_command(label='Mark Task Complete',
                             command=self.__taskListFrame.markComplete)
        filemenu.add_command(label='Save', command=self.__core.save)
        filemenu.add_command(label='Exit', command=self.destroy)
        self.__menuBar = tk.Menu(self)
        self.__menuBar.add_cascade(label='File', menu=filemenu)

        debugmenu = tk.Menu(self.__menuBar, tearoff=0)
        debugmenu.add_command(label='Print Projects',
                              command=self.__printProjects)
        debugmenu.add_command(label='test', command=self.__test)
        self.__menuBar.add_cascade(label="Debug", menu=debugmenu)
        self.config(menu=self.__menuBar)

        self.bind("<Control-Shift-C>", self.__taskListFrame.markComplete)
        self.bind("<Control-Shift-A>", self.__addTask)
        self.bind("<Control-s>", self.save)
        self.bind("<F5>", self.__redraw)

    def __printProjects(self):
        print([project.name for project in self.__taskList.getProjects()])

    def __addProject(self, event=None):
        if self.__taskListFrame is None or self.__projectListFrame is None:
            raise RuntimeError()
        self.__log.info("Add Project clicked")
        AddProjectDialog(self, self.__taskList)
        self.__projectListFrame.draw()

    def __addTask(self, event=None):
        if self.__taskListFrame is None or self.__projectListFrame is None:
            raise RuntimeError()
        if len(self.__core.getProjects()) == 0:
            self.__log.warning("No projects")
            return
        AddTaskDialog(self, self.__core)
        self.__taskListFrame.draw()

    def __redraw(self, event=None):
        if self.__taskListFrame is None or self.__projectListFrame is None:
            raise RuntimeError()
        self.__taskListFrame.draw()
        self.__projectListFrame.draw()

    def save(self, event=None):
        self.__taskList.save()

    def __test(self, event=None):
        pass




def main():
    configPath = Path(appdirs.user_config_dir(ProjectLog.__appname__), 'config.yaml')
    print(f'Config path is {configPath}')
    config = Config.instance(configPath=configPath)

    logName = config.logPath
    print(f"Logging to {logName}")
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    consoleOutput = logging.StreamHandler(sys.stdout)
    consoleOutput.setLevel(logging.WARNING)
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d: %(levelname)s:%(name)s: %(message)s', datefmt='%Y-%M-%d %H:%m:%S')
    consoleOutput.setFormatter(formatter)
    logger.addHandler(consoleOutput)

    logName.parent.mkdir(parents=True, exist_ok=True)
    fileOutput = logging.handlers.RotatingFileHandler(logName, maxBytes=5*1024*1024, backupCount=2)
    fileOutput.setLevel(logging.DEBUG)
    fileOutput.setFormatter(formatter)
    logger.addHandler(fileOutput)

    app = ProjectLogApp()
    app.mainloop()


if __name__ == '__main__':
    main()
