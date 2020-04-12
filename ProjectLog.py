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
# 04/12/20    NH    Added redraw on edit, added save on edit, fixed project list
#                   view
# 04/07/20    NH    Added date based highlighting, fixed date types
# 04/06/20    NH    Implemented GUI for ProjectListViewer, AddProjectDialog, and
#                   AddTaskDialog, and implemented shortcut keys for basic
#                   functionality
# 04/05/20    NH    Implemented GUI for TaskListViewer, added branch info
# 02/17/20    NH    Initial commit
#
###############################################################################
import datetime as dt
from enum import Enum
import tkinter as tk
import xml.etree.ElementTree as ET
import logging
import tkcalendar as tkc
import tkinter.messagebox as tkm
import sys
import os
import uuid

MAJOR_VERSION = 0
MINOR_VERSION = 0
BUILD_NUMBER = 1
BRANCH = "NH0"

BACKGROUND_COLOR = '#d9d9d9'
SELECTION_COLOR = '#a9def9'
OVERDUE_COLOR = '#f4a3a3'
UPCOMING_COLOR = '#ebec7f'


class Project:
    def __init__(self, name: str, endDate: dt.date, uid=None):
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
        if uid is None:
            uid = uuid.uuid4()
        self.__id = uid

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
        return hash(self.__id)

    def getName(self):
        return self.name

    def __str__(self):
        return "{Project: %s - %s}" % (self.name, self.endDate.strftime("%m/%d/%y"))

    def removeTask(self, task):
        self._tasks.remove(task)

    def getID(self):
        return str(self.__id)

    def getDate(self):
        return self.endDate

    def setName(self, name):
        self.name = name

    def setDate(self, date: dt.datetime):
        self.endDate = date

    def hasTasks(self):
        return len(self._tasks) > 0


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

    def __init__(self, dueDate: dt.date, project: Project,
                 desc: str, action: Action = Action.DO, uid=None):
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
        if uid is None:
            uid = uuid.uuid4()
        self.__id = uid

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
                if self.action.value < other.action.value:
                    return True
                elif self.action.value > other.action.value:
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

    def getID(self):
        return str(self.__id)


class TaskList:
    def __init__(self, fname):
        self._tasks = []
        self.__projects = []
        self.__fname = fname
        self.__log = logging.getLogger('ProjectLog.TaskList')
        self.__log.info('created')
        self.__enter__()

    def __enter__(self):
        self.__log.info('TaskList __enter__')
        if not os.path.isfile(self.__fname):
            # need to add empty structure
            self.save()
        tree = ET.parse(self.__fname)
        data = tree.getroot()
        if data.tag != 'data':
            raise RuntimeError("Data element not found")
        tasks = data.find('tasks')
        projects = data.find('projects')
        self._tasks = []
        self.__projects = []

        projectMap = {}
        actionMap = {}
        for action in Task.Action:
            actionMap[Task.ActionStringMap[action]] = action

        for project in projects:
            projectName = project.attrib['name']
            projectID = uuid.UUID(project.attrib['id'])
            projectDate = dt.datetime.strptime(
                project.attrib['date'], '%m/%d/%y').date()
            projectObj = Project(projectName, projectDate, projectID)
            self.__projects.append(projectObj)
            projectMap[projectID] = projectObj

        for task in tasks:
            taskID = uuid.UUID(task.attrib['id'])
            projectID = uuid.UUID(task.attrib['project'])
            project = projectMap[projectID]
            taskDate = dt.datetime.strptime(
                task.attrib['date'], '%m/%d/%y').date()
            taskAction = actionMap[task.attrib['action']]
            taskDesc = task.text
            taskObj = Task(taskDate, project, taskDesc, taskAction, taskID)
            self._tasks.append(taskObj)

        return self

    def open(self):
        self.__enter__()

    def close(self):
        self.__exit__(None, None, None)

    def save(self, *args):
        root = ET.Element('data')
        root.set('version', '1')
        tasks = ET.SubElement(root, 'tasks')
        projects = ET.SubElement(root, 'projects')

        # add projects
        for project in self.__projects:
            projectElement = ET.SubElement(projects, 'project')
            projectElement.set('id', project.getID())
            projectElement.set('name', project.getName())
            projectElement.set('date', project.getDate().strftime('%m/%d/%y'))

        # add tasks
        for task in self._tasks:
            taskElement = ET.SubElement(tasks, 'task')
            taskElement.set('id', task.getID())
            taskElement.set('project', task.getProject().getID())
            taskElement.set('date', task.getDate().strftime('%m/%d/%y'))
            taskElement.set('action', Task.ActionStringMap[task.getAction()])
            taskElement.text = task.getDesc()

        tree = ET.ElementTree(root)
        tree.write(self.__fname)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__log.info('__exit__')
        if exc_val is not None:
            self.__log.exception("Got %s", str(exc_val))
        self.save()

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

    def removeProject(self, project: Project):
        if project.hasTasks():
            tkm.showerror(
                title='Error', message='Project still has active tasks')
            return
        self.__projects.remove(project)

    def removeTask(self, task: Task):
        self._tasks.remove(task)
        task.getProject().removeTask(task)


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
    SELECTED_TASK_WIDGET_VIEW = {'bg': SELECTION_COLOR}

    NORMAL_TASK_FRAME_VIEW = {
        'highlightbackground': 'black', 'highlightthickness': 1}
    NORMAL_TASK_WIDGET_VIEW = {'bg': BACKGROUND_COLOR}

    OVERDUE_TASK_FRAME_VIEW = {
        'highlightbackground': 'black', 'highlightthickness': 1}
    OVERDUE_TASK_WIDGET_VIEW = {'bg': OVERDUE_COLOR}

    UPCOMING_TASK_FRAME_VIEW = {
        'highlightbackground': 'black', 'highlightthickness': 1}
    UPCOMING_TASK_WIDGET_VIEW = {'bg': UPCOMING_COLOR}

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
        self.__frame = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.draw()

    def draw(self):
        if self.__frame is not None:
            self.__frame.destroy()
        self.__taskMap = {}
        self.__frameMap = {}
        self.__widgetMap = {}
        self.__taskSelected = None
        self.__currentInputType = None
        self.__currentInputWidget = None
        self.__inputVarTraceID = None

        self.__frame = tk.Frame(self)
        self.__frame.grid(row=0, column=0, sticky='nesw')
        self.__frame.grid_columnconfigure(0, weight=1)

        headingFrame = tk.Frame(self.__frame)
        headingFrame.grid(row=0, column=0, sticky='ew')

        for column in TaskListViewer.ColumnProperties:
            headingFrame.grid_columnconfigure(
                column.value['index'], minsize=column.value['width'], weight=column.value['weight'])
            tk.Label(headingFrame, text=column.value['label'], anchor='w').grid(
                row=0, column=column.value['index'], sticky='ew')

        row = 1
        for task in sorted(self.__model.getTasks()):
            dueDate = task.getDate()
            frameView, widgetView = self.getViewDefs(dueDate)

            taskFrame = tk.Frame(self.__frame)
            taskFrame.configure(**frameView)
            taskFrame.grid(row=row, column=0, sticky='ew')
            for column in TaskListViewer.ColumnProperties:
                taskFrame.grid_columnconfigure(
                    column.value['index'], minsize=column.value['width'], weight=column.value['weight'])
            self.__frameMap[task] = taskFrame

            datelabel = tk.Label(
                taskFrame, text=task.dueDate.strftime('%a, %b %d'), anchor='w', **widgetView)
            datelabel.grid(
                row=0, column=TaskListViewer.ColumnProperties.DATE.value['index'], sticky='ew')
            datelabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
            datelabel.bind('<Button-1>', self._onTaskSingleClick)
            self.__taskMap[datelabel] = task

            projectLabel = tk.Label(
                taskFrame, text=task.project.name, anchor='w', **widgetView)
            projectLabel.grid(
                row=0, column=TaskListViewer.ColumnProperties.PROJECT.value['index'], sticky='ew')
            projectLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
            projectLabel.bind('<Button-1>', self._onTaskSingleClick)
            self.__taskMap[projectLabel] = task

            actionLabel = tk.Label(
                taskFrame, text=Task.ActionStringMap[task.action], anchor='w', **widgetView)
            actionLabel.grid(
                row=0, column=TaskListViewer.ColumnProperties.ACTION.value['index'], sticky='ew')
            actionLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
            actionLabel.bind('<Button-1>', self._onTaskSingleClick)
            self.__taskMap[actionLabel] = task

            descLabel = tk.Label(
                taskFrame, text=task.desc, anchor='w', **widgetView)
            descLabel.grid(
                row=0, column=TaskListViewer.ColumnProperties.DESCRIPTION.value['index'], sticky='ew')
            descLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
            descLabel.bind('<Button-1>', self._onTaskSingleClick)
            self.__taskMap[descLabel] = task

            self.__widgetMap[task] = [datelabel,
                                      projectLabel, actionLabel, descLabel]
            row += 1

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
            frameView, widgetView = self.getViewDefs(
                self.__taskSelected.getDate())
            self.__frameMap[self.__taskSelected].configure(
                **frameView)
            for widget in self.__widgetMap[self.__taskSelected]:
                widget.configure(**widgetView)
            frame.configure(**TaskListViewer.SELECTED_TASK_FRAME_VIEW)
            for widget in widgets:
                widget.configure(**TaskListViewer.SELECTED_TASK_WIDGET_VIEW)
            self.__taskSelected = task

        # Set current widget to edit mode
        self.__taskMap.pop(event.widget)
        event.widget.destroy()
        if event.widget is widgets[0]:
            date = task.getDate()

            dateEntry = tkc.DateEntry(
                frame, textvariable=self.__inputVar, firstweekday='sunday', year=date.year, month=date.month, day=date.day)
            dateEntry.grid(
                row=0, column=TaskListViewer.ColumnProperties.DATE.value['index'], sticky='ew')
            dateEntry.bind('<<DateEntrySelected>>', self._onDateEntered)

            widgets[0] = dateEntry
            self.__currentInputWidget = dateEntry
            self.__currentInputType = TaskListViewer.ColumnProperties.DATE
        elif event.widget is widgets[1]:
            # replace with dropdown
            self.__inputVar.set(task.getProject().getName())
            projectMenu = tk.OptionMenu(
                frame, self.__inputVar, *(project.name for project in self.__model.getProjects()))
            projectMenu.configure(takefocus=1)
            projectMenu.grid(
                row=0, column=TaskListViewer.ColumnProperties.PROJECT.value['index'], sticky='ew')
            self.__inputVarTraceID = self.__inputVar.trace(
                'w', self._onProjectSelected)

            widgets[1] = projectMenu
            self.__currentInputWidget = projectMenu
            self.__currentInputType = TaskListViewer.ColumnProperties.PROJECT
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
        elif event.widget is widgets[3]:
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
        self.__taskMap[self.__currentInputWidget] = task
        self.__currentInputWidget.focus_set()

    def _onTaskSingleClick(self, event):
        task = self.__taskMap[event.widget]

        if self.__currentInputType != None:
            frameView, widgetView = self.getViewDefs(
                self.__taskSelected.getDate())

        # Cancel current input
        if self.__currentInputType == TaskListViewer.ColumnProperties.DATE:

            parent = self.__currentInputWidget.master
            self.__taskMap.pop(self.__currentInputWidget)
            self.__currentInputWidget.grid_remove()
            self.__currentInputType = None
            self.__currentInputWidget = None

            datelabel = tk.Label(
                parent, text=self.__taskSelected.dueDate.strftime('%a, %b %d'), anchor='w', **widgetView)
            datelabel.grid(
                row=0, column=TaskListViewer.ColumnProperties.DATE.value['index'], sticky='ew')
            datelabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
            datelabel.bind('<Button-1>', self._onTaskSingleClick)

            self.__taskMap[datelabel] = self.__taskSelected
            self.__widgetMap[self.__taskSelected][0] = datelabel
        elif self.__currentInputType == TaskListViewer.ColumnProperties.PROJECT:
            parent = self.__currentInputWidget.master
            self.__taskMap.pop(self.__currentInputWidget)
            self.__currentInputWidget.grid_remove()
            self.__currentInputType = None
            self.__currentInputWidget = None

            projectLabel = tk.Label(
                parent, text=self.__taskSelected.project.name, anchor='w', **widgetView)
            projectLabel.grid(
                row=0, column=TaskListViewer.ColumnProperties.PROJECT.value['index'], sticky='ew')
            projectLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
            projectLabel.bind('<Button-1>', self._onTaskSingleClick)

            self.__taskMap[projectLabel] = self.__taskSelected
            self.__widgetMap[self.__taskSelected][1] = projectLabel
            self.__inputVar.trace_vdelete('w', self.__inputVarTraceID)
        elif self.__currentInputType == TaskListViewer.ColumnProperties.ACTION:
            parent = self.__currentInputWidget.master
            self.__taskMap.pop(self.__currentInputWidget)
            self.__currentInputWidget.grid_remove()
            self.__currentInputType = None
            self.__currentInputWidget = None

            actionLabel = tk.Label(
                parent, text=Task.ActionStringMap[self.__taskSelected.action], anchor='w', **widgetView)
            actionLabel.grid(
                row=0, column=TaskListViewer.ColumnProperties.ACTION.value['index'], sticky='ew')
            actionLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
            actionLabel.bind('<Button-1>', self._onTaskSingleClick)

            self.__taskMap[actionLabel] = self.__taskSelected
            self.__widgetMap[self.__taskSelected][2] = actionLabel
            self.__inputVar.trace_vdelete('w', self.__inputVarTraceID)
        elif self.__currentInputType == TaskListViewer.ColumnProperties.DESCRIPTION:
            parent = self.__currentInputWidget.master
            self.__taskMap.pop(self.__currentInputWidget)
            self.__currentInputWidget.grid_remove()
            self.__currentInputType = None
            self.__currentInputWidget = None

            descLabel = tk.Label(
                parent, text=self.__taskSelected.desc, anchor='w', **widgetView)
            descLabel.grid(
                row=0, column=TaskListViewer.ColumnProperties.DESCRIPTION.value['index'], sticky='ew')
            descLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
            descLabel.bind('<Button-1>', self._onTaskSingleClick)

            self.__taskMap[descLabel] = self.__taskSelected
            self.__widgetMap[self.__taskSelected][3] = descLabel

        # Toggle select current task
        frame = self.__frameMap[task]
        widgets = self.__widgetMap[task]
        if task is self.__taskSelected:
            # Deselect current task
            frameView, widgetView = self.getViewDefs(task.getDate())
            frame.configure(**frameView)
            for widget in widgets:
                widget.configure(**widgetView)
            self.__taskSelected = None
        elif self.__taskSelected is None:
            # select from nothing else
            frame.configure(**TaskListViewer.SELECTED_TASK_FRAME_VIEW)
            for widget in widgets:
                widget.configure(**TaskListViewer.SELECTED_TASK_WIDGET_VIEW)
            self.__taskSelected = task
        else:
            frameView, widgetView = self.getViewDefs(
                self.__taskSelected.getDate())
            # select from someone else
            self.__frameMap[self.__taskSelected].configure(
                **frameView)
            for widget in self.__widgetMap[self.__taskSelected]:
                widget.configure(**widgetView)
            frame.configure(**TaskListViewer.SELECTED_TASK_FRAME_VIEW)
            for widget in widgets:
                widget.configure(**TaskListViewer.SELECTED_TASK_WIDGET_VIEW)
            self.__taskSelected = task

    def _onDateEntered(self, event):
        # Update date
        task = self.__taskMap[event.widget]

        task.setDate(dt.datetime.strptime(
            self.__inputVar.get(), '%m/%d/%y').date())

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
        self.draw()
        self.__model.save()

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
        self.draw()
        self.__model.save()

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
        self.draw()
        self.__model.save()

    def _onDescEntered(self, event):
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
        self.draw()
        self.__model.save()

    def markComplete(self, event=None):
        task = self.__taskSelected
        self.__model.removeTask(task)
        self.draw()
        self.__model.save()

    def getViewDefs(self, dueDate):
        today = dt.date.today()
        # this is the date before which things are upcoming
        limitDate = (today + dt.timedelta(days=7))
        if dueDate <= today:
            frameView = TaskListViewer.OVERDUE_TASK_FRAME_VIEW
            widgetView = TaskListViewer.OVERDUE_TASK_WIDGET_VIEW
        elif dueDate <= limitDate:
            frameView = TaskListViewer.UPCOMING_TASK_FRAME_VIEW
            widgetView = TaskListViewer.UPCOMING_TASK_WIDGET_VIEW
        else:
            frameView = TaskListViewer.NORMAL_TASK_FRAME_VIEW
            widgetView = TaskListViewer.NORMAL_TASK_WIDGET_VIEW
        return frameView, widgetView


class ProjectListviewer(tk.Frame):

    class Columns(Enum):
        NAME = {'index': 1, 'width': 120, 'label': 'Project', 'weight': 1}
        DATE = {'index': 0, 'width': 85, 'label': 'Date', 'weight': 0}

    SELECTED_PROJECT_FRAME_VIEW = {
        "highlightbackground": 'black', 'highlightthickness': 1}
    SELECTED_PROJECT_WIDGET_VIEW = {'bg': SELECTION_COLOR}
    NORMAL_PROJECT_FRAME_VIEW = {
        'highlightbackground': 'black', 'highlightthickness': 1}
    NORMAL_PROJECT_WIDGET_VIEW = {'bg': BACKGROUND_COLOR}

    def __init__(self, parent, model: TaskList):
        super().__init__(parent)
        self.__model = model
        self.__dataFrame = None
        self.__inputVar = tk.StringVar()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.draw()

    def draw(self):
        if self.__dataFrame is not None:
            self.__dataFrame.destroy()

        self.__dataFrame = tk.Frame(self)
        self.__dataFrame.grid(row=0, column=0, sticky='nesw')
        self.__dataFrame.grid_rowconfigure(0, weight=1)
        self.__dataFrame.grid_columnconfigure(0, weight=1)

        headingFrame = tk.Frame(self.__dataFrame)
        headingFrame.grid(row=0, column=0, sticky='ew')
        for column in ProjectListviewer.Columns:
            headingFrame.grid_columnconfigure(
                column.value['index'], minsize=column.value['width'], weight=column.value['weight'])
            tk.Label(headingFrame, text=column.value['label'], anchor='w').grid(
                row=0, column=column.value['index'], sticky='ew')

        row = 1

        self.__projectMap = {}
        self.__frameMap = {}
        self.__widgetMap = {}
        self.__projectSelected = None

        self.__currentInputType = None
        self.__currentInputWidget = None

        for project in sorted(self.__model.getProjects()):
            projectFrame = tk.Frame(
                self.__dataFrame, **ProjectListviewer.NORMAL_PROJECT_FRAME_VIEW)
            projectFrame.grid(row=row, column=0, sticky='ew')
            for column in ProjectListviewer.Columns:
                projectFrame.grid_columnconfigure(
                    column.value['index'], minsize=column.value['width'], weight=column.value['weight'])
            self.__frameMap[project] = projectFrame

            nameLabel = tk.Label(projectFrame, text=project.name, anchor='w')
            nameLabel.grid(
                row=row, column=ProjectListviewer.Columns.NAME.value['index'], sticky='ew')
            nameLabel.bind('<Double-Button-1>', self._onProjectDoubleClick)
            nameLabel.bind('<Button-1>', self._onProjectSingleClick)
            self.__projectMap[nameLabel] = project

            dateLabel = tk.Label(projectFrame, text=project.getDate().strftime(
                '%m/%d/%Y'), anchor='w')
            dateLabel.grid(
                row=row, column=ProjectListviewer.Columns.DATE.value['index'], sticky='ew')
            dateLabel.bind('<Double-Button-1>', self._onProjectDoubleClick)
            dateLabel.bind('<Button-1>', self._onProjectSingleClick)
            self.__projectMap[dateLabel] = project

            self.__widgetMap[project] = [nameLabel, dateLabel]

            row += 1
        self.__dataFrame.grid(row=0, column=0)

    def _onProjectDoubleClick(self, event):
        project = self.__projectMap[event.widget]
        frame = self.__frameMap[project]
        widgets = self.__widgetMap[project]

        if self.__projectSelected is None:
            # select from nothing else
            frame.configure(**ProjectListviewer.SELECTED_PROJECT_FRAME_VIEW)
            for widget in widgets:
                widget.configure(
                    **ProjectListviewer.SELECTED_PROJECT_WIDGET_VIEW)
            self.__projectSelected = project
        else:
            self.__frameMap[self.__projectSelected].configure(
                **ProjectListviewer.NORMAL_PROJECT_FRAME_VIEW)
            for widget in self.__widgetMap[self.__projectSelected]:
                widget.configure(
                    **ProjectListviewer.NORMAL_PROJECT_WIDGET_VIEW)

            frame.configure(**ProjectListviewer.SELECTED_PROJECT_FRAME_VIEW)
            for widget in widgets:
                widget.configure(
                    **ProjectListviewer.SELECTED_PROJECT_WIDGET_VIEW)

            self.__projectSelected = project

        # set current widget to edit mode
        self.__projectMap.pop(event.widget)
        event.widget.destroy()

        if event.widget is widgets[0]:
            # name widget
            self.__inputVar.set(project.getName())

            descEntry = tk.Entry(frame, textvariable=self.__inputVar)
            descEntry.grid(
                row=0, column=ProjectListviewer.Columns.NAME.value['index'], sticky='ew')
            descEntry.bind('<Return>', self._onNameEntered)
            descEntry.bind('<KP_Enter>', self._onNameEntered)
            descEntry.focus_set()

            widgets[0] = descEntry
            self.__currentInputWidget = descEntry
            self.__currentInputType = ProjectListviewer.Columns.NAME
            self.__projectMap[descEntry] = project
        else:
            # date widget
            date = project.getDate()

            dateEntry = tkc.DateEntry(frame, textvariable=self.__inputVar,
                                      firstweekday='sunday', year=date.year, month=date.month, day=date.day)
            dateEntry.grid(
                row=0, column=ProjectListviewer.Columns.DATE.value['index'], sticky='ew')
            dateEntry.bind('<<DateEntrySelected>>', self._onDateEntered)

            widgets[1] = dateEntry
            self.__currentInputWidget = dateEntry
            self.__currentInputType = ProjectListviewer.Columns.DATE
            self.__projectMap[dateEntry] = project

    def _onProjectSingleClick(self, event):
        project = self.__projectMap[event.widget]

        # cancel current input
        if self.__currentInputType == ProjectListviewer.Columns.DATE:
            parent = self.__currentInputWidget.master
            self.__projectMap.pop(self.__currentInputWidget)
            self.__currentInputWidget.grid_remove()
            self.__currentInputType = None
            self.__currentInputWidget = None

            dateLabel = tk.Label(parent, text=self.__projectSelected.getDate().strftime(
                '%m/%d/%Y'), anchor='w', **ProjectListviewer.NORMAL_PROJECT_WIDGET_VIEW)
            dateLabel.grid(
                row=0, column=ProjectListviewer.Columns.DATE.value['index'], sticky='ew')
            dateLabel.bind('<Double-Button-1>', self._onProjectDoubleClick)
            dateLabel.bind('<Button-1>', self._onProjectSingleClick)

            self.__projectMap[dateLabel] = self.__projectSelected
            self.__widgetMap[self.__projectSelected][1] = dateLabel
        elif self.__currentInputType == ProjectListviewer.Columns.NAME:
            parent = self.__currentInputWidget.master
            self.__projectMap.pop(self.__currentInputWidget)
            self.__currentInputWidget.grid_remove()
            self.__currentInputType = None
            self.__currentInputWidget = None

            descLabel = tk.Label(parent, text=self.__projectSelected.getName(
            ), anchor='w', **ProjectListviewer.NORMAL_PROJECT_WIDGET_VIEW)
            descLabel.grid(
                row=0, column=ProjectListviewer.Columns.NAME.value['index'], sticky='ew')
            descLabel.bind('<Double-Button-1>', self._onProjectDoubleClick)
            descLabel.bind('<Button-1>', self._onProjectSingleClick)

            self.__projectMap[descLabel] = self.__projectSelected
            self.__widgetMap[self.__projectSelected][0] = descLabel

        # Toggle current project
        frame = self.__frameMap[project]
        widgets = self.__widgetMap[project]
        if project is self.__projectSelected:
            # deselect current project
            frame.configure(**ProjectListviewer.NORMAL_PROJECT_FRAME_VIEW)
            for widget in widgets:
                widget.configure(
                    **ProjectListviewer.NORMAL_PROJECT_WIDGET_VIEW)
            self.__projectSelected = None
        elif self.__projectSelected is None:
            # select from nothing else
            frame.configure(**ProjectListviewer.SELECTED_PROJECT_FRAME_VIEW)
            for widget in widgets:
                widget.configure(
                    **ProjectListviewer.SELECTED_PROJECT_WIDGET_VIEW)
            self.__projectSelected = project
        else:
            self.__frameMap[self.__projectSelected].configure(
                **ProjectListviewer.NORMAL_PROJECT_FRAME_VIEW)
            for widget in self.__widgetMap[self.__projectSelected]:
                widget.configure(
                    **ProjectListviewer.NORMAL_PROJECT_WIDGET_VIEW)

            frame.configure(**ProjectListviewer.SELECTED_PROJECT_FRAME_VIEW)
            for widget in widgets:
                widget.configure(
                    **ProjectListviewer.SELECTED_PROJECT_WIDGET_VIEW)
            self.__projectSelected = project

    def _onNameEntered(self, event):
        project = self.__projectMap[event.widget]

        name = self.__inputVar.get()
        project.setName(name)

        parent = self.__currentInputWidget.master
        self.__projectMap.pop(self.__currentInputWidget)
        self.__currentInputWidget.grid_remove()
        self.__currentInputType = None
        self.__currentInputWidget = None

        descLabel = tk.Label(parent, text=project.getName(
        ), anchor='w', **ProjectListviewer.SELECTED_PROJECT_WIDGET_VIEW)
        descLabel.grid(
            row=0, column=ProjectListviewer.Columns.NAME.value['index'], sticky='ew')
        descLabel.bind('<Double-Button-1>', self._onProjectDoubleClick)
        descLabel.bind('<Button-1>', self._onProjectSingleClick)

        self.__projectMap[descLabel] = project
        self.__widgetMap[project][0] = descLabel
        self.draw()
        self.__model.save()

    def _onDateEntered(self, event):
        # Update date
        project = self.__projectMap[event.widget]

        project.setDate(dt.datetime.strptime(
            self.__inputVar.get(), '%m/%d/%y'))

        parent = self.__currentInputWidget.master
        self.__projectMap.pop(self.__currentInputWidget)
        self.__currentInputWidget.grid_remove()
        self.__currentInputType = None
        self.__currentInputWidget = None

        dateLabel = tk.Label(parent, text=project.getDate().strftime(
            '%m/%d/%Y'), anchor='w', **ProjectListviewer.SELECTED_PROJECT_WIDGET_VIEW)
        dateLabel.grid(
            row=0, column=ProjectListviewer.Columns.DATE.value['index'], sticky='ew')
        dateLabel.bind('<Double-Button-1>', self._onProjectDoubleClick)
        dateLabel.bind('<Button-1>', self._onProjectSingleClick)

        self.__projectMap[dateLabel] = project
        self.__widgetMap[project][1] = dateLabel
        self.draw()
        self.__model.save()

    def removeProject(self):
        if self.__projectSelected is None:
            return
        self.__model.removeProject(self.__projectSelected)
        self.draw()
        self.__model.save()


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
        self.__descVar = tk.StringVar()
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
        self.grid_columnconfigure(0, weight=1)

        dateEntry = tkc.DateEntry(self.__bodyFrame, textvariable=self.__dateSelector,
                                  mindate=dt.datetime.today().date(), firstweekday='sunday')
        dateEntry.grid(row=0, column=0, sticky='ew')

        projectMenu = tk.OptionMenu(self.__bodyFrame, self.__projectSelector, *
                                    (project.name for project in sorted(self.__taskList.getProjects())))
        projectMenu.configure(takefocus=1)
        projectMenu.grid(row=1, column=0, sticky='ew')

        actionMenu = tk.OptionMenu(self.__bodyFrame, self.__actionSelector, *
                                   (Task.ActionStringMap[action] for action in Task.Action))
        actionMenu.configure(takefocus=1)
        actionMenu.grid(row=2, column=0, sticky='ew')

        descEntry = tk.Entry(self.__bodyFrame, textvariable=self.__descVar)
        descEntry.grid(row=3, column=0, sticky='ew')
        descEntry.bind('<Return>', self.__ok)
        descEntry.bind('<KP_Enter>', self.__ok)

        buttonFrame = tk.Frame(self.__bodyFrame)
        buttonFrame.grid_columnconfigure(0, weight=1)
        buttonFrame.grid_columnconfigure(1, weight=1)
        buttonFrame.grid(row=4, column=0, sticky='ew')

        okButton = tk.Button(buttonFrame, text='OK', command=self.__ok)
        okButton.grid(row=0, column=0, sticky='ew')

        cancelButton = tk.Button(
            buttonFrame, text='Cancel', command=self.__cancel)
        cancelButton.grid(row=0, column=1, sticky='ew')
        self.__bodyFrame.grid(row=0, column=0)

        self.bind('<Escape>', self.__cancel)
        dateEntry.focus_set()

    def __ok(self, event=None):
        self.withdraw()
        self.update_idletasks()

        dueDate = dt.datetime.strptime(
            self.__dateSelector.get(), '%m/%d/%y').date()
        project = self.__taskList.getProjectByName(
            self.__projectSelector.get())
        desc = self.__descVar.get()

        for action in Task.Action:
            if Task.ActionStringMap[action] == self.__actionSelector.get():
                break

        task = Task(dueDate, project, desc, action)
        self.__taskList.addTask(task)
        self.__cancel()

    def __cancel(self, event=None):
        self.__parent.focus_set()
        self.destroy()


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
            self.__bodyFrame, textvariable=self.__dateSelector, mindate=dt.date.today(), firstweekday='sunday')
        self.__dateEntry.grid(row=0, column=1, sticky='ew')

        tk.Label(self.__bodyFrame, text='Project Name:').grid(
            row=1, column=0, sticky='ew')
        nameEntry = tk.Entry(
            self.__bodyFrame, textvariable=self.__projectNamevar)
        nameEntry.grid(row=1, column=1, sticky='ew')
        nameEntry.bind('<Return>', self.__ok)
        nameEntry.bind('<KP_Enter>', self.__ok)

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
            self.__dateSelector.get(), '%m/%d/%y').date())
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

        self.title("Project Task Tracker v%d.%d.%d.%s" %
                   (MAJOR_VERSION, MINOR_VERSION, BUILD_NUMBER, BRANCH))
        self.__createWidgets()
        self.__createMenu()
        self.protocol('WM_DELETE_WINDOW', self.__deleteWindowHandler)

    def __deleteWindowHandler(self):
        self.__taskList.close()
        self.destroy()

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
        filemenu.add_command(label='Remove Project',
                             command=self.__projectListFrame.removeProject)
        filemenu.add_command(label='Mark Task Complete',
                             command=self.__taskListFrame.markComplete)
        filemenu.add_command(label='Save', command=self.__taskList.save)
        filemenu.add_command(label='Exit', command=self.destroy)
        self.__menuBar = tk.Menu(self)
        self.__menuBar.add_cascade(label='File', menu=filemenu)

        debugmenu = tk.Menu(self.__menuBar, tearoff=0)
        debugmenu.add_command(label='Print Projects',
                              command=self.__printProjects)
        debugmenu.add_command(label='d1', command=self.__taskListFrame.debug)
        self.__menuBar.add_cascade(label="Debug", menu=debugmenu)
        self.config(menu=self.__menuBar)

        self.bind("<Control-Shift-C>", self.__taskListFrame.markComplete)
        self.bind("<Control-Shift-A>", self.__addTask)
        self.bind("<Control-s>", self.save)
        self.bind("<F5>", self.__redraw)

    def __printProjects(self):
        print([project.name for project in self.__taskList.getProjects()])

    def __addProject(self, event=None):
        self.__log.info("Add Project clicked")
        AddProjectDialog(self, self.__taskList)
        self.__projectListFrame.draw()

    def __addTask(self, event=None):
        if len(self.__taskList.getProjects()) == 0:
            self.__log.warning("No projects")
            return
        AddTaskDialog(self, self.__taskList)
        self.__taskListFrame.draw()

    def __redraw(self, event=None):
        self.__taskListFrame.draw()
        self.__projectListFrame.draw()

    def save(self, event=None):
        self.__taskList.save()


if __name__ == '__main__':
    global app
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

    app = ProjectLog()
    app.mainloop()
