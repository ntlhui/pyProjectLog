#!/usr/bin/env python3
###############################################################################
#     Radio Collar Tracker Ground Control Software
#     Copyright (C) 2020  Nathan Hui
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
#
# DATE        Name  Description
# -----------------------------------------------------------------------------
# 04/05/20    NH    Implemented GUI for TaskListViewer
# 02/17/20    NH    Initial commit
#
###############################################################################
import datetime as dt
from enum import Enum
import tkinter as tk
import xml.etree.ElementTree as ET
import logging
import tkcalendar as tkc
import sys
import os


class Project:
    def __init__(self, name: str, endDate: dt.date):
        '''
        Creates a new Project object
        :param name: Project name
        :type name: str
        :param endDate: Project end date
        :type endDate: dt.date
        '''
        self.name = name
        self.endDate = endDate
        self._tasks = []
        self.__log = logging.getLogger("ProjectLog.Project")

    def addTask(self, task):
        if task in self._tasks:
            raise RuntimeError("Task already in project")
        self._tasks.append(task)

    def __eq__(self, other):
        return self.name == other.name and self.endDate == other.endDate

    def __lt__(self, other):
        if self.endDate < other.endDate:
            return True
        elif self.endDate > other.endDate:
            return False
        else:
            return self.name < other.name

    def __hash__(self):
        return hash((self.endDate, self.name))

    def getName(self):
        return self.name

    def __str__(self):
        return "{Project: %s - %s}" % (self.name, self.endDate.strftime("%m/%d/%y"))

    def removeTask(self, task):
        self._tasks.remove(task)


class Task:
    class Action(Enum):
        DO = 1
        READ = 2
        PREPARE = 3
        WRITE = 4
        ATTEND = 5
        LEARN = 6
        BRING = 7
        DUE = 8
        FINISH = 9
        PRINT = 10
        WATCH = 11

    ActionStringMap = {
        Action.DO: "Do",
        Action.READ: "Read",
        Action.PREPARE: "Prepare",
        Action.WRITE: "Write",
        Action.ATTEND: "Attend",
        Action.LEARN: "Learn",
        Action.BRING: "Bring",
        Action.DUE: "Due",
        Action.FINISH: "Finish",
        Action.PRINT: "Print",
        Action.WATCH: "Watch",
    }

    taskCount = 0

    def __init__(self, dueDate: dt.date, project: Project,
                 desc: str, action: Action = Action.DO):
        '''
        Creates a new Task object
        :param dueDate:    Due date
        :type dueDate:    dt.date
        :param project:    Associated project
        :type project:    Project
        :param desc:    Description
        :type desc:    str
        :param action:    Action
        :type action:    Action
        '''
        self.dueDate = dueDate
        self.project = project
        self.desc = desc
        self.action = action
        self.project.addTask(self)
        self.__id = Task.taskCount
        Task.taskCount += 1

    def __eq__(self, other):
        return self is other

    def __lt__(self, other):
        if self.dueDate < other.dueDate:
            return True
        elif self.dueDate > other.dueDate:
            return False
        else:
            if self.project < other.project:
                return True
            elif self.project > other.project:
                return False
            else:
                if self.action < other.action:
                    return True
                elif self.action > other.action:
                    return False
                else:
                    return self.desc < other.desc

    def __hash__(self):
        return hash(self.__id)

    def __str__(self):
        return "{Task: %s: %s - %s by %s}" % (self.project, Task.ActionStringMap[self.action], self.desc, self.dueDate)

    def setDate(self, date: dt.date):
        self.dueDate = date

    def getDate(self):
        return self.dueDate

    def getProject(self):
        return self.project

    def setProject(self, project: Project):
        self.project.removeTask(self)
        self.project = project
        self.project.addTask(self)

    def getAction(self):
        return self.action

    def setAction(self, action: Action):
        self.action = action

    def getDesc(self):
        return self.desc

    def setDesc(self, desc):
        self.desc = desc


class TaskList:
    def __init__(self, fname):
        global DEBUG_PROJECT
        global DEBUG_PROJECT1
        global DEBUG_TASK
        self._tasks = []
        self.__projects = []
        self.__fname = fname
        self.__file = None
        self.__log = logging.getLogger('ProjectLog.TaskList')
        self.__log.info('created')

        self.addProject(DEBUG_PROJECT)
        self.addProject(DEBUG_PROJECT1)
        self.addTask(DEBUG_TASK)

    def __enter__(self):
        self.__log.info('TaskList __enter__')
        if not os.path.isfile(self.__fname):
            with open(self.__fname, 'w') as ofile:
                ofile.write(ET.dump(ET.Element('Project Log')))
        ET.parse(self.__fname)
        return self

    def open(self):
        self.__enter__()

    def close(self):
        self.__exit__(None, None, None)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__log.info('__exit__')
        if exc_val is not None:
            self.__log.exception("Got %s", str(exc_val))
        self.__file.close()

    def addProject(self, project: Project):
        '''
        Adds a project to the task list
        :param project: Project
        :type project: Project
        '''
        self.__log.info('Added project %s' % project.name)
        self.__projects.append(project)

    def addTask(self, task: Task):
        self.__log.info('Added task due %s for project %s to %s' %
                        (task.dueDate.ctime(), task.project.name, task.desc))
        self._tasks.append(task)

    def getTasks(self):
        return self._tasks

    def getProjects(self):
        return self.__projects

    def getProjectByName(self, name: str):
        for project in self.__projects:
            if project.getName() == name:
                return project

        return None


class TaskListViewer(tk.Frame):
    class ColumnProperties(Enum):
        COLLAPSE = {'index': 0, 'width': 20, 'label': '', 'weight': 0}
        DATE = {'index': 1, 'width': 120, 'label': 'Date', 'weight': 0}
        PROJECT = {'index': 2, 'width': 150, 'label': 'Project', 'weight': 0}
        ACTION = {'index': 3, 'width': 90, 'label': 'Action', 'weight': 0}
        DESCRIPTION = {'index': 4, 'width': 300,
                       'label': "Description", 'weight': 1}

    SELECTED_TASK_FRAME_VIEW = {
        "highlightbackground": 'black', 'highlightthickness': 1}
    SELECTED_TASK_WIDGET_VIEW = {'bg': "#A9DEF9"}
    NORMAL_TASK_FRAME_VIEW = {
        'highlightbackground': 'black', 'highlightthickness': 1}
    NORMAL_TASK_WIDGET_VIEW = {'bg': '#d9d9d9'}

    def debug(self):
        print(self.debugWidget.winfo_width())

    def __init__(self, parent, model: TaskList):
        super().__init__(parent)
        self.__model = model
        self.__taskMap = {}
        self.__frameMap = {}
        self.__taskSelected = None
        self.__widgetMap = {}
        self.__inputVar = tk.StringVar()
        self.__currentInputWidget = None
        self.__currentInputType = None
        self.__inputVarTraceID = None

        self.grid_columnconfigure(0, weight=1)

        headingFrame = tk.Frame(self)
        headingFrame.grid(row=0, column=0, sticky='ew')

        for column in TaskListViewer.ColumnProperties:
            headingFrame.grid_columnconfigure(
                column.value['index'], minsize=column.value['width'], weight=column.value['weight'])
            tk.Label(headingFrame, text=column.value['label'], anchor='w').grid(
                row=0, column=column.value['index'], sticky='ew')

        row = 1
        for task in sorted(self.__model.getTasks()):
            taskFrame = tk.Frame(self)
            taskFrame.configure(**TaskListViewer.NORMAL_TASK_FRAME_VIEW)
            taskFrame.grid(row=row, column=0, sticky='ew')
            for column in TaskListViewer.ColumnProperties:
                taskFrame.grid_columnconfigure(
                    column.value['index'], minsize=column.value['width'], weight=column.value['weight'])
            self.__frameMap[task] = taskFrame

            datelabel = tk.Label(
                taskFrame, text=task.dueDate.strftime('%a, %b %d'), anchor='w', **TaskListViewer.NORMAL_TASK_WIDGET_VIEW)
            datelabel.grid(
                row=0, column=TaskListViewer.ColumnProperties.DATE.value['index'], sticky='ew')
            datelabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
            datelabel.bind('<Button-1>', self._onTaskSingleClick)
            self.__taskMap[datelabel] = task

            projectLabel = tk.Label(
                taskFrame, text=task.project.name, anchor='w', **TaskListViewer.NORMAL_TASK_WIDGET_VIEW)
            projectLabel.grid(
                row=0, column=TaskListViewer.ColumnProperties.PROJECT.value['index'], sticky='ew')
            projectLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
            projectLabel.bind('<Button-1>', self._onTaskSingleClick)
            self.__taskMap[projectLabel] = task

            actionLabel = tk.Label(
                taskFrame, text=Task.ActionStringMap[task.action], anchor='w', **TaskListViewer.NORMAL_TASK_WIDGET_VIEW)
            actionLabel.grid(
                row=0, column=TaskListViewer.ColumnProperties.ACTION.value['index'], sticky='ew')
            actionLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
            actionLabel.bind('<Button-1>', self._onTaskSingleClick)
            self.__taskMap[actionLabel] = task

            descLabel = tk.Label(
                taskFrame, text=task.desc, anchor='w', **TaskListViewer.NORMAL_TASK_WIDGET_VIEW)
            descLabel.grid(
                row=0, column=TaskListViewer.ColumnProperties.DESCRIPTION.value['index'], sticky='ew')
            descLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
            descLabel.bind('<Button-1>', self._onTaskSingleClick)
            self.__taskMap[descLabel] = task

            self.__widgetMap[task] = [datelabel,
                                      projectLabel, actionLabel, descLabel]

    def _onTaskDoubleClick(self, event):
        # Select current task
        task = self.__taskMap[event.widget]
        frame = self.__frameMap[task]
        widgets = self.__widgetMap[task]
        if self.__taskSelected is None:
            # select from nothing else
            frame.configure(**TaskListViewer.SELECTED_TASK_FRAME_VIEW)
            for widget in widgets:
                widget.configure(**TaskListViewer.SELECTED_TASK_WIDGET_VIEW)
            self.__taskSelected = task
        else:
            # select from someone else
            self.__frameMap[self.__taskSelected].configure(
                **TaskListViewer.NORMAL_TASK_FRAME_VIEW)
            for widget in self.__widgetMap[self.__taskSelected]:
                widget.configure(**TaskListViewer.NORMAL_TASK_WIDGET_VIEW)
            frame.configure(**TaskListViewer.SELECTED_TASK_FRAME_VIEW)
            for widget in widgets:
                widget.configure(**TaskListViewer.SELECTED_TASK_WIDGET_VIEW)
            self.__taskSelected = task
        # Set current widget to edit mode
        self.__taskMap.pop(event.widget)
        event.widget.destroy()
        if event.widget is widgets[0]:
            date = task.getDate().date()

            dateEntry = tkc.DateEntry(
                frame, textvariable=self.__inputVar, firstweekday='sunday', year=date.year, month=date.month, day=date.day)
            dateEntry.grid(
                row=0, column=TaskListViewer.ColumnProperties.DATE.value['index'], sticky='ew')
            dateEntry.bind('<<DateEntrySelected>>', self._onDateEntered)

            widgets[0] = dateEntry
            self.__currentInputWidget = dateEntry
            self.__currentInputType = TaskListViewer.ColumnProperties.DATE
            self.__taskMap[dateEntry] = task
        elif event.widget is widgets[1]:
            # replace with dropdown
            self.__inputVar.set(task.getProject().getName())
            projectMenu = tk.OptionMenu(
                frame, self.__inputVar, *(project.name for project in self.__model.getProjects()))
            projectMenu.grid(
                row=0, column=TaskListViewer.ColumnProperties.PROJECT.value['index'], sticky='ew')
            self.__inputVarTraceID = self.__inputVar.trace(
                'w', self._onProjectSelected)

            widgets[1] = projectMenu
            self.__currentInputWidget = projectMenu
            self.__currentInputType = TaskListViewer.ColumnProperties.PROJECT
            self.__taskMap[projectMenu] = task
        elif event.widget is widgets[2]:
            # replace with dropdown
            self.__inputVar.set(Task.ActionStringMap[task.getAction()])
            actionMenu = tk.OptionMenu(
                frame, self.__inputVar, *(Task.ActionStringMap[action] for action in Task.Action))
            actionMenu.grid(
                row=0, column=TaskListViewer.ColumnProperties.ACTION.value['index'], sticky='ew')
            self.__inputVarTraceID = self.__inputVar.trace(
                'w', self._onActionSelected)

            widgets[2] = actionMenu
            self.__currentInputWidget = actionMenu
            self.__currentInputType = TaskListViewer.ColumnProperties.ACTION
            self.__taskMap[actionMenu] = task
        elif event.widget is widgets[3]:
            print("Clicked on desc")
            # replace with entry
            self.__inputVar.set(task.getDesc())
            descEntry = tk.Entry(frame, textvariable=self.__inputVar)
            descEntry.grid(
                row=0, column=TaskListViewer.ColumnProperties.DESCRIPTION.value['index'], sticky='ew')
            descEntry.bind('<Return>', self._onDescEntered)
            descEntry.bind('<KP_Enter>', self._onDescEntered)
            descEntry.focus_set()

            widgets[3] = descEntry
            self.__currentInputWidget = descEntry
            self.__currentInputType = TaskListViewer.ColumnProperties.DESCRIPTION
            self.__taskMap[descEntry] = task

    def _onTaskSingleClick(self, event):
        task = self.__taskMap[event.widget]
        # Cancel current input
        if self.__currentInputType == TaskListViewer.ColumnProperties.DATE:
            parent = self.__currentInputWidget.master
            self.__taskMap.pop(self.__currentInputWidget)
            self.__currentInputWidget.grid_remove()
            self.__currentInputType = None
            self.__currentInputWidget = None

            datelabel = tk.Label(
                parent, text=task.dueDate.strftime('%a, %b %d'), anchor='w', **TaskListViewer.NORMAL_TASK_WIDGET_VIEW)
            datelabel.grid(
                row=0, column=TaskListViewer.ColumnProperties.DATE.value['index'], sticky='ew')
            datelabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
            datelabel.bind('<Button-1>', self._onTaskSingleClick)

            self.__taskMap[datelabel] = task
            self.__widgetMap[task][0] = datelabel
        elif self.__currentInputType == TaskListViewer.ColumnProperties.PROJECT:
            parent = self.__currentInputWidget.master
            self.__taskMap.pop(self.__currentInputWidget)
            self.__currentInputWidget.grid_remove()
            self.__currentInputType = None
            self.__currentInputWidget = None

            projectLabel = tk.Label(
                parent, text=task.project.name, anchor='w', **TaskListViewer.NORMAL_TASK_WIDGET_VIEW)
            projectLabel.grid(
                row=0, column=TaskListViewer.ColumnProperties.PROJECT.value['index'], sticky='ew')
            projectLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
            projectLabel.bind('<Button-1>', self._onTaskSingleClick)

            self.__taskMap[projectLabel] = task
            self.__widgetMap[task][1] = projectLabel
            self.__inputVar.trace_vdelete('w', self.__inputVarTraceID)
        elif self.__currentInputType == TaskListViewer.ColumnProperties.ACTION:
            parent = self.__currentInputWidget.master
            self.__taskMap.pop(self.__currentInputWidget)
            self.__currentInputWidget.grid_remove()
            self.__currentInputType = None
            self.__currentInputWidget = None

            actionLabel = tk.Label(
                parent, text=Task.ActionStringMap[task.action], anchor='w', **TaskListViewer.NORMAL_TASK_WIDGET_VIEW)
            actionLabel.grid(
                row=0, column=TaskListViewer.ColumnProperties.ACTION.value['index'], sticky='ew')
            actionLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
            actionLabel.bind('<Button-1>', self._onTaskSingleClick)

            self.__taskMap[actionLabel] = task
            self.__widgetMap[task][2] = actionLabel
            self.__inputVar.trace_vdelete('w', self.__inputVarTraceID)
        elif self.__currentInputType == TaskListViewer.ColumnProperties.DESCRIPTION:
            parent = self.__currentInputWidget.master
            self.__taskMap.pop(self.__currentInputWidget)
            self.__currentInputWidget.grid_remove()
            self.__currentInputType = None
            self.__currentInputWidget = None

            descLabel = tk.Label(
                parent, text=task.desc, anchor='w', **TaskListViewer.NORMAL_TASK_WIDGET_VIEW)
            descLabel.grid(
                row=0, column=TaskListViewer.ColumnProperties.DESCRIPTION.value['index'], sticky='ew')
            descLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
            descLabel.bind('<Button-1>', self._onTaskSingleClick)

            self.__taskMap[descLabel] = task
            self.__widgetMap[task][3] = descLabel

        # Toggle select current task
        frame = self.__frameMap[task]
        widgets = self.__widgetMap[task]
        if task is self.__taskSelected:
            # Deselect current task
            frame.configure(**TaskListViewer.NORMAL_TASK_FRAME_VIEW)
            for widget in widgets:
                widget.configure(**TaskListViewer.NORMAL_TASK_WIDGET_VIEW)
            self.__taskSelected = None
        elif self.__taskSelected is None:
            # select from nothing else
            frame.configure(**TaskListViewer.SELECTED_TASK_FRAME_VIEW)
            for widget in widgets:
                widget.configure(**TaskListViewer.SELECTED_TASK_WIDGET_VIEW)
            self.__taskSelected = task
        else:
            # select from someone else
            self.__frameMap[self.__taskSelected].configure(
                **TaskListViewer.NORMAL_TASK_FRAME_VIEW)
            for widget in self.__widgetMap[self.__taskSelected]:
                widget.configure(**TaskListViewer.NORMAL_TASK_WIDGET_VIEW)
            frame.configure(**TaskListViewer.SELECTED_TASK_FRAME_VIEW)
            for widget in widgets:
                widget.configure(**TaskListViewer.SELECTED_TASK_WIDGET_VIEW)
            self.__taskSelected = task

    def _onDateEntered(self, event):
        # Update date
        task = self.__taskMap[event.widget]

        task.setDate(dt.datetime.strptime(self.__inputVar.get(), '%m/%d/%y'))

        parent = self.__currentInputWidget.master
        self.__taskMap.pop(self.__currentInputWidget)
        self.__currentInputWidget.grid_remove()
        self.__currentInputType = None
        self.__currentInputWidget = None

        datelabel = tk.Label(
            parent, text=task.dueDate.strftime('%a, %b %d'), anchor='w', **TaskListViewer.SELECTED_TASK_WIDGET_VIEW)
        datelabel.grid(
            row=0, column=TaskListViewer.ColumnProperties.DATE.value['index'], sticky='ew')
        datelabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
        datelabel.bind('<Button-1>', self._onTaskSingleClick)

        self.__taskMap[datelabel] = task
        self.__widgetMap[task][0] = datelabel

    def _onProjectSelected(self, *args):
        # Update project
        task = self.__taskMap[self.__currentInputWidget]

        project = self.__model.getProjectByName(self.__inputVar.get())
        task.setProject(project)

        parent = self.__currentInputWidget.master
        self.__taskMap.pop(self.__currentInputWidget)
        self.__currentInputWidget.grid_remove()
        self.__currentInputType = None
        self.__currentInputWidget = None

        projectLabel = tk.Label(
            parent, text=task.project.name, anchor='w', **TaskListViewer.SELECTED_TASK_WIDGET_VIEW)
        projectLabel.grid(
            row=0, column=TaskListViewer.ColumnProperties.PROJECT.value['index'], sticky='ew')
        projectLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
        projectLabel.bind('<Button-1>', self._onTaskSingleClick)

        self.__taskMap[projectLabel] = task
        self.__widgetMap[task][1] = projectLabel
        self.__inputVar.trace_vdelete('w', self.__inputVarTraceID)

    def _onActionSelected(self, *args):
        # Update action
        task = self.__taskMap[self.__currentInputWidget]

        for action in Task.Action:
            if Task.ActionStringMap[action] == self.__inputVar.get():
                break
        task.setAction(action)

        parent = self.__currentInputWidget.master
        self.__taskMap.pop(self.__currentInputWidget)
        self.__currentInputWidget.grid_remove()
        self.__currentInputType = None
        self.__currentInputWidget = None

        actionLabel = tk.Label(
            parent, text=Task.ActionStringMap[task.action], anchor='w', **TaskListViewer.SELECTED_TASK_WIDGET_VIEW)
        actionLabel.grid(
            row=0, column=TaskListViewer.ColumnProperties.ACTION.value['index'], sticky='ew')
        actionLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
        actionLabel.bind('<Button-1>', self._onTaskSingleClick)

        self.__taskMap[actionLabel] = task
        self.__widgetMap[task][2] = actionLabel
        self.__inputVar.trace_vdelete('w', self.__inputVarTraceID)

    def _onDescEntered(self, event):
        print("Desc entered")
        task = self.__taskMap[event.widget]

        desc = self.__inputVar.get()
        task.setDesc(desc)

        parent = self.__currentInputWidget.master
        self.__taskMap.pop(self.__currentInputWidget)
        self.__currentInputWidget.grid_remove()
        self.__currentInputType = None
        self.__currentInputWidget = None

        descLabel = tk.Label(
            parent, text=task.desc, anchor='w', **TaskListViewer.SELECTED_TASK_WIDGET_VIEW)
        descLabel.grid(
            row=0, column=TaskListViewer.ColumnProperties.DESCRIPTION.value['index'], sticky='ew')
        descLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
        descLabel.bind('<Button-1>', self._onTaskSingleClick)

        self.__taskMap[descLabel] = task
        self.__widgetMap[task][3] = descLabel


class ProjectListviewer(tk.Frame):
    def __init__(self, parent, model: TaskList):
        super().__init__(parent)
        self.__model = model
        self.__dataFrame = None

        self.draw()

    def draw(self):
        if self.__dataFrame:
            self.__dataFrame.destroy()
        self.__dataFrame = tk.Frame(self)
        self.__dataFrame.grid_columnconfigure(0, minsize=150)
        self.__dataFrame.grid_columnconfigure(1, minsize=150)
        tk.Label(self.__dataFrame, text='Project',
                 anchor='w').grid(row=0, column=0, sticky='ew')
        tk.Label(self.__dataFrame, text='Due Date',
                 anchor='w').grid(row=0, column=1, sticky='ew')
        row = 1
        for project in sorted(self.__model.getProjects()):
            tk.Label(self.__dataFrame, text=project.name, anchor='w').grid(
                row=row, column=0, sticky='ew')
            tk.Label(self.__dataFrame, text=project.endDate.strftime(
                '%m/%d/%Y'), anchor='w').grid(row=row, column=1, sticky='ew')
            row += 1
        self.__dataFrame.grid(row=0, column=0)


class AddTaskDialog(tk.Toplevel):
    def __init__(self, parent, tasklist):
        self.__parent = parent
        self.__taskList = tasklist
        self.__bodyFrame = None
        self.__acceptFrame = None
        self.__initial_focus = None
        self.__dateSelector = tk.StringVar()
        self.__actionSelector = tk.StringVar()
        self.__actionSelector.set(Task.ActionStringMap[Task.Action.DO])
        self.__projectSelector = tk.StringVar()
        tk.Toplevel.__init__(self, parent)

        self.transient(parent)
        self.title("Add Task")
        self.__createWidget()
#         self.protocol("WM_DELETE_WINDOW", self.d)
        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50,
                                  parent.winfo_rooty() + 50))

        self.wait_window(self)

    def __createWidget(self):
        if self.__bodyFrame:
            self.__bodyFrame.destroy()
        self.__bodyFrame = tk.Frame(self)
        self.__dateEntry = tkc.DateEntry(
            self.__bodyFrame, textvariable=self.__dateSelector, mindate=dt.datetime.today().date())
        self.__dateEntry.grid(row=0, column=0, columnspan=2, sticky='ew')
        tk.OptionMenu(self, self.__projectSelector, *
                      (project.name for project in sorted(self.__taskList.getProjects())))
        tk.OptionMenu(self, self.__actionSelector, *
                      tuple(Task.ActionStringMap.values())).grid(row=2, column=0, columnspan=2, sticky='ew')
        self.__bodyFrame.grid(row=0, column=0)


class AddProjectDialog(tk.Toplevel):
    def __init__(self, parent, tasklist):
        tk.Toplevel.__init__(self, parent)
        self.__parent = parent
        self.__bodyFrame = None
        self.__dateSelector = tk.StringVar()
        self.__projectNamevar = tk.StringVar()
        self.__taskList = tasklist
        self.__log = logging.getLogger('ProjectLog.AddProject')

        self.transient(parent)
        self.title("Add Project")
        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50,
                                  parent.winfo_rooty() + 50))

        self.__createWidget()

        self.wait_window(self)

    def __createWidget(self):
        if self.__bodyFrame:
            self.__bodyFrame.destroy()
        self.__bodyFrame = tk.Frame(self)
        self.__bodyFrame.grid_rowconfigure(0, weight=1)
        self.__bodyFrame.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        tk.Label(self.__bodyFrame, text='End Date:').grid(
            row=0, column=0)
        self.__dateEntry = tkc.DateEntry(
            self.__bodyFrame, textvariable=self.__dateSelector, mindate=dt.date.today())
        self.__dateEntry.grid(row=0, column=1, sticky='ew')

        tk.Label(self.__bodyFrame, text='Project Name:').grid(
            row=1, column=0, sticky='ew')
        tk.Entry(self.__bodyFrame, textvariable=self.__projectNamevar).grid(
            row=1, column=1, sticky='ew')

        self.__bodyFrame.grid(row=0, column=0, sticky='ew')

        buttonFrame = tk.Frame(self)

        okButton = tk.Button(buttonFrame, text='OK', command=self.__ok)
        okButton.grid(row=0, column=0)

        cancelButton = tk.Button(
            buttonFrame, text='Cancel', command=self.__cancel)
        cancelButton.grid(row=0, column=1)

        buttonFrame.grid(row=1, column=0)

    def __cancel(self, event=None):
        self.__log.info("User cancelled")
        self.__parent.focus_set()
        self.destroy()

    def __ok(self, event=None):
        self.__log.info("User confirmed")
        self.withdraw()
        self.update_idletasks()

#         apply
        project = Project(self.__projectNamevar.get(), dt.datetime.strptime(
            self.__dateSelector.get(), '%m/%d/%y'))
        self.__taskList.addProject(project)
        self.__cancel()


class ProjectLog(tk.Tk):
    def __init__(self):
        super().__init__()
        self.__log = logging.getLogger('ProjectLog.ProjectLog')
        self.__log.info("created")
        self.__menuBar = None  # type: tk.Menu
        self.__taskListFrame = None
        self.__projectListFrame = None  # type: tk.Frame
        self.__taskList = TaskList("test.xml")
#         self.__taskList.open()

        self.title("Project Task Tracker")
        self.__createWidgets()
        self.__createMenu()

    def __createWidgets(self):
        self.grid_columnconfigure(0, weight=1, pad=5)
        self.grid_columnconfigure(1, pad=5)
        self.grid_rowconfigure(0, weight=1)
        self.__taskListFrame = TaskListViewer(self, self.__taskList)
        self.__taskListFrame.grid(row=0, column=0, sticky='new')
        self.__projectListFrame = ProjectListviewer(self, self.__taskList)
        self.__projectListFrame.grid(row=0, column=1, sticky='new')

    def __createMenu(self):
        if self.__menuBar is not None:
            self.__menuBar.destroy()
        filemenu = tk.Menu(self.__menuBar, tearoff=0)
        filemenu.add_command(label='Add Project', command=self.__addProject)
        filemenu.add_command(label='Add Task', command=self.__addTask)
        filemenu.add_command(label='Exit', command=self.destroy)
        self.__menuBar = tk.Menu(self)
        self.__menuBar.add_cascade(label='File', menu=filemenu)

        debugmenu = tk.Menu(self.__menuBar, tearoff=0)
        debugmenu.add_command(label='Print Projects',
                              command=self.__printProjects)
        debugmenu.add_command(label='d1', command=self.__taskListFrame.debug)
        self.__menuBar.add_cascade(label="Debug", menu=debugmenu)
        self.config(menu=self.__menuBar)

    def __printProjects(self):
        print([project.name for project in self.__taskList.getProjects()])

    def __addProject(self):
        self.__log.info("Add Project clicked")
        d = AddProjectDialog(self, self.__taskList)
        self.__projectListFrame.draw()

    def __addTask(self):
        if len(self.__taskList.getProjects()) == 0:
            self.__log.warning("No projects")
            return
        d = AddTaskDialog(self, self.__taskList)


if __name__ == '__main__':
    global DEBUG_PROJECT
    global DEBUG_PROJECT1
    global DEBUG_TASK
    DEBUG_PROJECT = Project("DebugProject", dt.datetime(2020, 12, 31))
    DEBUG_PROJECT1 = Project("DebugProject1", dt.datetime(2021, 12, 31))
    DEBUG_TASK = Task(dt.datetime(2020, 5, 1), DEBUG_PROJECT,
                      "Debug Task")
    logName = dt.datetime.now().strftime('%Y.%m.%d.%H.%M.%S.log')
    logName = 'log.log'
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    consoleOutput = logging.StreamHandler(sys.stdout)
    consoleOutput.setLevel(logging.WARNING)
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d: %(levelname)s:%(name)s: %(message)s', datefmt='%Y-%M-%d %H:%m:%S')
    consoleOutput.setFormatter(formatter)
    logger.addHandler(consoleOutput)
    fileOutput = logging.FileHandler(logName)
    fileOutput.setLevel(logging.DEBUG)
    fileOutput.setFormatter(formatter)
    logger.addHandler(fileOutput)

    ProjectLog().mainloop()
