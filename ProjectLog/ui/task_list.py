from __future__ import annotations
import datetime as dt
import logging
import re
import tkinter as tk
from dataclasses import dataclass
from typing import Dict, Optional, Union
from uuid import UUID

import tkcalendar as tkc
from ProjectLog.firebase import TaskLog
from ProjectLog.data import Recurrence, Task, Project
from ProjectLog.ui.dialog import RecurrenceDialog
from ProjectLog.ui.theme import ThemeManager
from ProjectLog.ui.widgets import SelectableComboBox


class TaskListViewer(tk.Frame):
    @dataclass
    class ColumnProperty:
        index: int
        width: int
        label: str
        weight: int

    COLLAPSE = 1
    DATE = 2
    PROJECT = 3
    ACTION = 4
    DESCRIPTION = 5
    RECURRENCE = 6

    ColumnProperties = {
        COLLAPSE: ColumnProperty(index=0, width=20, label='', weight=0),
        DATE: ColumnProperty(index=1, width=120, label='Date', weight=0),
        PROJECT: ColumnProperty(index=2, width=150, label='Project', weight=0),
        ACTION: ColumnProperty(index=3, width=90, label='Action', weight=0),
        DESCRIPTION: ColumnProperty(index=4, width=300, label='Description', weight=1),
        RECURRENCE: ColumnProperty(
            index=5, width=20, label='Recurring', weight=0)
    }

    SELECTED_TASK_FRAME_VIEW = {
        "highlightbackground": 'black', 'highlightthickness': 1}
    SELECTED_TASK_WIDGET_VIEW = {'bg': ThemeManager.SELECTION_COLOR}

    NORMAL_TASK_FRAME_VIEW = {
        'highlightbackground': 'black', 'highlightthickness': 1}
    NORMAL_TASK_WIDGET_VIEW = {'bg': ThemeManager.BACKGROUND_COLOR}

    OVERDUE_TASK_FRAME_VIEW = {
        'highlightbackground': 'black', 'highlightthickness': 1}
    OVERDUE_TASK_WIDGET_VIEW = {'bg': ThemeManager.OVERDUE_COLOR}

    UPCOMING_TASK_FRAME_VIEW = {
        'highlightbackground': 'black', 'highlightthickness': 1}
    UPCOMING_TASK_WIDGET_VIEW = {'bg': ThemeManager.UPCOMING_COLOR}

    def __init__(self, parent, model: TaskLog):
        super().__init__(parent)
        self.__log = logging.getLogger("TaskListViewer")
        self.__model = model
        self.__taskMap: Dict[UUID, TaskListViewer.TaskEntry] = {}
        self.__widgetMap: Dict[tk.Widget, UUID] = {}
        self.__inputVar = tk.StringVar()
        self.__inputVarTraceID = None
        self.__filterVar = tk.StringVar()
        self.__activeTaskEntry: Optional[TaskListViewer.TaskEntry] = None
        self.__currentInputColumn: Optional[int] = None
        self.__frame = None
        self.__filterPattern = '.*'

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.draw()

    def draw(self):
        self.__log.debug("drawing")
        if self.__frame is not None:
            self.__frame.destroy()

        self.__headingWidgets = {}

        self.__frame = tk.Frame(self)
        self.__frame.grid(row=0, column=0, sticky='nesw')
        self.__frame.grid_columnconfigure(0, weight=1)

        self.__headingFrame = tk.Frame(self.__frame)
        self.__headingFrame.grid(row=0, column=0, sticky='ew')

        for column in TaskListViewer.ColumnProperties.values():
            self.__headingFrame.grid_columnconfigure(
                column.index, minsize=column.width, weight=column.weight)
            headingWidget = tk.Label(
                self.__headingFrame, text=column.label, anchor='w')
            headingWidget.grid(
                row=0, column=column.index, sticky='ew')
            headingWidget.bind('<Double-Button-1>', self._onHeadingDoubleClick)
            self.__headingWidgets[headingWidget] = column

        self._drawTasks()

    def _onHeadingDoubleClick(self, event):
        self.__log.debug("_onHeadingDoubleClick")
        column = self.__headingWidgets[event.widget]
        if column == TaskListViewer.ACTION:
            pass
        elif column == TaskListViewer.COLLAPSE:
            pass
        elif column == TaskListViewer.DATE:
            pass
        elif column == TaskListViewer.DESCRIPTION:
            pass
        elif column == TaskListViewer.PROJECT:
            self.__filterVar.set('All')
            projectMenu = tk.OptionMenu(self.__headingFrame, self.__filterVar, "All", *(
                project.name for project in self.__model.getProjects()))
            projectMenu.configure(takefocus=1)
            projectMenu.grid(row=0, column=column.value['index'], sticky='ew')
            self.__filterVarTraceID = self.__filterVar.trace(
                'w', self._onFilterSelected)
            projectMenu.bind('<Button-3>', self._onHeadingRightClick)
            self.__headingWidgets[projectMenu] = column
        else:
            print("ERROR")

    def _onHeadingRightClick(self, event):
        self.__log.debug("_onHeadingRightClick")
        column = self.__headingWidgets[event.widget]
        if column == TaskListViewer.ACTION:
            pass
        elif column == TaskListViewer.COLLAPSE:
            pass
        elif column == TaskListViewer.DATE:
            pass
        elif column == TaskListViewer.DESCRIPTION:
            pass
        elif column == TaskListViewer.PROJECT:
            self.__filterVar.set('All')
            event.widget.destroy()
            self.__headingWidgets.pop(event.widget)
        else:
            print("ERROR")

    def _onTaskDoubleClick(self, event):
        self.__log.debug("_onTaskDoubleClick")
        # Select current task
        task_id = self.__widgetMap[event.widget]
        task_entry = self.__taskMap[task_id]

        if self.__activeTaskEntry is None:
            # select from nothing else
            task_entry.frame.configure(
                **TaskListViewer.SELECTED_TASK_FRAME_VIEW)
            for widget in task_entry.frame.winfo_children():
                widget.configure(**TaskListViewer.SELECTED_TASK_WIDGET_VIEW)
            self.__activeTaskEntry = task_entry
        else:
            # select from someone else
            frameView, widgetView = self.getViewDefs(
                self.__activeTaskEntry.task.dueDate)
            self.__activeTaskEntry.frame.configure(
                **frameView)
            for widget in self.__activeTaskEntry.frame.winfo_children():
                widget.configure(**widgetView)
            task_entry.frame.configure(
                **TaskListViewer.SELECTED_TASK_FRAME_VIEW)
            for widget in task_entry.frame.winfo_children():
                widget.configure(**TaskListViewer.SELECTED_TASK_WIDGET_VIEW)
            self.__activeTaskEntry = task_entry

        # Set current widget to edit mode
        self.__widgetMap.pop(event.widget)
        event.widget.destroy()
        if event.widget is task_entry.dateLabel:
            column_property = TaskListViewer.ColumnProperties[self.DATE]
            date = task_entry.task.dueDate

            dateEntry = tkc.DateEntry(
                task_entry.frame, textvariable=self.__inputVar, firstweekday='sunday', year=date.year, month=date.month, day=date.day)
            dateEntry.grid(
                row=0,
                column=column_property.index, sticky='ew')
            dateEntry.bind('<<DateEntrySelected>>', self._onDateEntered)

            task_entry.dateLabel = dateEntry
            new_input_widget = dateEntry
            self.__currentInputColumn = self.DATE
        elif event.widget is task_entry.projectLabel:
            # replace with dropdown
            column_property = TaskListViewer.ColumnProperties[self.PROJECT]
            project = task_entry.task.project
            if not isinstance(project, Project):
                raise RuntimeError
            self.__inputVar.set(project.name)
            projectMap = {
                project.name: project for project in self.__model.getProjects()}
            projectMenu = SelectableComboBox(
                master=task_entry.frame,
                initial_value=project.name,
                values=projectMap,
                onSelectCb=self._onProjectSelected,
                cb_kwargs={
                    'task_entry': task_entry
                }
            )
            projectMenu.configure(takefocus=1)
            projectMenu.grid(
                row=0, column=column_property.index, sticky='ew')

            task_entry.projectLabel = projectMenu
            new_input_widget = projectMenu
            self.__currentInputColumn = self.PROJECT
        elif event.widget is task_entry.actionLabel:
            column_property = TaskListViewer.ColumnProperties[self.ACTION]
            # replace with dropdown
            self.__inputVar.set(Task.ActionStringMap[task_entry.task.action])
            action_options = {
                Task.ActionStringMap[action]: action for action in Task.Action
            }
            actionMenu = SelectableComboBox(
                master=task_entry.frame,
                initial_value=Task.ActionStringMap[task_entry.task.action],
                values=action_options,
                onSelectCb=self._onActionSelected,
                cb_kwargs={'task_entry': task_entry}
            )
            actionMenu.grid(
                row=0, column=column_property.index, sticky='ew')

            task_entry.actionLabel = actionMenu
            new_input_widget = actionMenu
            self.__currentInputColumn = self.ACTION
        elif event.widget is task_entry.descLabel:
            column_property = TaskListViewer.ColumnProperties[self.DESCRIPTION]
            # replace with entry
            self.__inputVar.set(task_entry.task.desc)
            descEntry = tk.Entry(
                task_entry.frame, textvariable=self.__inputVar)
            descEntry.grid(
                row=0, column=column_property.index, sticky='ew')
            descEntry.bind('<Return>', self._onDescEntered)
            descEntry.bind('<KP_Enter>', self._onDescEntered)
            descEntry.focus_set()

            task_entry.descLabel = descEntry
            new_input_widget = descEntry
            self.__currentInputColumn = self.DESCRIPTION
        elif event.widget is task_entry.recurLabel:
            # open dialog
            recurrence = task_entry.task.recurrence
            if isinstance(recurrence, Recurrence):
                RecurrenceDialog(self, recurrence)
            else:
                dialog = RecurrenceDialog(
                    self, dueDate=task_entry.task.dueDate)
                task_entry.task.recurrence = dialog.recurrence
            new_input_widget = task_entry.recurLabel
        else:
            raise RuntimeError

        self.__widgetMap[new_input_widget] = task_id
        new_input_widget.focus_set()

    def _onTaskSingleClick(self, event: tk.Event):
        self.__log.debug("_onTaskSingleClick")
        # Select current task
        task_id = self.__widgetMap[event.widget]
        selected_task_entry = self.__taskMap[task_id]
        active_task_entry = self.__activeTaskEntry

        if self.__currentInputColumn != None:
            assert(self.__activeTaskEntry is not None)
            frameView, widgetView = self.getViewDefs(
                self.__activeTaskEntry.task.dueDate)

        if active_task_entry:
            # Cancel active input
            if self.__currentInputColumn == self.DATE:
                column_properties = TaskListViewer.ColumnProperties[self.DATE]
                self.__widgetMap.pop(active_task_entry.dateLabel)
                active_task_entry.dateLabel.destroy()

                datelabel = tk.Label(
                    active_task_entry.frame, text=active_task_entry.task.dueDate.strftime('%a, %b %d'), anchor='w', **widgetView)
                datelabel.grid(
                    row=0, column=column_properties.index, sticky='ew')
                datelabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
                datelabel.bind('<Button-1>', self._onTaskSingleClick)

                self.__widgetMap[datelabel] = task_id
                active_task_entry.dateLabel = datelabel
            elif self.__currentInputColumn == self.PROJECT:
                column_properties = TaskListViewer.ColumnProperties[self.PROJECT]
                self.__widgetMap.pop(active_task_entry.projectLabel)
                active_task_entry.projectLabel.destroy()

                projectLabel = tk.Label(
                    active_task_entry.frame, text=active_task_entry.task.project.name, anchor='w', **widgetView)
                projectLabel.grid(
                    row=0, column=column_properties.index, sticky='ew')
                projectLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
                projectLabel.bind('<Button-1>', self._onTaskSingleClick)

                self.__widgetMap[projectLabel] = task_id
                active_task_entry.projectLabel = projectLabel
            elif self.__currentInputColumn == self.ACTION:
                column_properties = TaskListViewer.ColumnProperties[self.ACTION]
                self.__widgetMap.pop(active_task_entry.actionLabel)
                active_task_entry.actionLabel.destroy()

                actionLabel = tk.Label(
                    active_task_entry.frame, text=Task.ActionStringMap[active_task_entry.task.action], anchor='w', **widgetView)
                actionLabel.grid(
                    row=0, column=column_properties.index, sticky='ew')
                actionLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
                actionLabel.bind('<Button-1>', self._onTaskSingleClick)

                self.__widgetMap[actionLabel] = task_id
                active_task_entry.actionLabel = actionLabel
            elif self.__currentInputColumn == self.DESCRIPTION:
                column_properties = TaskListViewer.ColumnProperties[self.DESCRIPTION]
                self.__widgetMap.pop(active_task_entry.descLabel)
                active_task_entry.descLabel.destroy()

                descLabel = tk.Label(
                    active_task_entry.frame,
                    text=active_task_entry.task.desc,
                    anchor='w', **widgetView)
                descLabel.grid(
                    row=0, column=column_properties.index, sticky='ew')
                descLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
                descLabel.bind('<Button-1>', self._onTaskSingleClick)

                self.__widgetMap[descLabel] = task_id
                active_task_entry.descLabel = descLabel

            self.__currentInputColumn = None

        # Toggle select current task
        if selected_task_entry is self.__activeTaskEntry:
            # Deselect current task
            frameView, widgetView = self.getViewDefs(
                selected_task_entry.task.dueDate)
            selected_task_entry.frame.configure(**frameView)
            for widget in selected_task_entry.frame.winfo_children():
                widget.configure(**widgetView)
            self.__activeTaskEntry = None
        elif self.__activeTaskEntry is None:
            # select from nothing else
            selected_task_entry.frame.configure(
                **TaskListViewer.SELECTED_TASK_FRAME_VIEW)
            for widget in selected_task_entry.frame.winfo_children():
                widget.configure(**TaskListViewer.SELECTED_TASK_WIDGET_VIEW)
            self.__activeTaskEntry = selected_task_entry
        else:
            frameView, widgetView = self.getViewDefs(
                self.__activeTaskEntry.task.dueDate)
            # select from someone else
            self.__activeTaskEntry.frame.configure(
                **frameView)
            for widget in self.__activeTaskEntry.frame.winfo_children():
                widget.configure(**widgetView)
            selected_task_entry.frame.configure(
                **TaskListViewer.SELECTED_TASK_FRAME_VIEW)
            for widget in selected_task_entry.frame.winfo_children():
                widget.configure(**TaskListViewer.SELECTED_TASK_WIDGET_VIEW)
            self.__activeTaskEntry = selected_task_entry

    def _onDateEntered(self, event: tk.Event):
        self.__log.debug("_onDateEntered")
        # Update date
        task_id = self.__widgetMap[event.widget]
        task_entry = self.__taskMap[task_id]
        task = task_entry.task

        task.dueDate = dt.datetime.strptime(
            self.__inputVar.get(), '%m/%d/%y').date()

        self.__widgetMap.pop(event.widget)
        event.widget.destroy()
        self.__currentInputColumn = None

        datelabel = self.createDateLabel2(
            task_entry.task, TaskListViewer.SELECTED_TASK_WIDGET_VIEW, task_entry.frame)

        self.__widgetMap[datelabel] = task_id
        task_entry.dateLabel = datelabel
        self.draw()
        self.__model.save()

    def _onFilterSelected(self, *args):
        self.__log.debug("_onFilterSelected")
        if self.__filterVar.get() == 'All':
            self.__filterPattern = '.*'
        else:
            self.__filterPattern = self.__filterVar.get()
        self._drawTasks()

    def _onProjectSelected(self, widget: SelectableComboBox, project: Project, task_entry: TaskEntry):
        self.__log.debug("_onProjectSelected")
        # Update project
        if task_entry is None:
            raise RuntimeError
        task = task_entry.task

        column_properties = TaskListViewer.ColumnProperties[self.PROJECT]

        task.project = project

        self.__widgetMap.pop(widget)
        widget.destroy()
        self.__currentInputColumn = None

        projectLabel = tk.Label(
            task_entry.frame, text=task.project.name, anchor='w', **TaskListViewer.SELECTED_TASK_WIDGET_VIEW)
        projectLabel.grid(
            row=0, column=column_properties.index, sticky='ew')
        projectLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
        projectLabel.bind('<Button-1>', self._onTaskSingleClick)

        self.__widgetMap[projectLabel] = task_entry.task.uid
        task_entry.projectLabel = projectLabel
        self.draw()
        self.__model.save()

    def _onActionSelected(self, widget: SelectableComboBox, action: Task.Action, task_entry: TaskEntry):
        self.__log.debug("_onActionSelected")
        # Update action
        column_properties = TaskListViewer.ColumnProperties[self.ACTION]
        task = task_entry.task

        task.action = action

        self.__widgetMap.pop(widget)
        widget.destroy()
        self.__currentInputColumn = None

        actionLabel = tk.Label(
            task_entry.frame, text=Task.ActionStringMap[task.action], anchor='w', **TaskListViewer.SELECTED_TASK_WIDGET_VIEW)
        actionLabel.grid(
            row=0, column=column_properties.index, sticky='ew')
        actionLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
        actionLabel.bind('<Button-1>', self._onTaskSingleClick)

        self.__widgetMap[actionLabel] = task.uid
        task_entry.actionLabel = actionLabel
        self.draw()
        self.__model.save()
    
    def __doProjectChangeHandler(self, project: Project, task_entry: TaskListViewer.TaskEntry):
        project_widget = task_entry.projectLabel
        if isinstance(project_widget, tk.Label):
            project_widget.configure(text=project.name)
            
    def _onDescEntered(self, event: tk.Event):
        self.__log.debug("_onDescEntered")
        column_properties = TaskListViewer.ColumnProperties[self.DESCRIPTION]
        task_id = self.__widgetMap[event.widget]
        task_entry = self.__taskMap[task_id]
        task = task_entry.task

        desc = self.__inputVar.get()
        task.desc = desc

        parent = task_entry.frame
        self.__widgetMap.pop(event.widget)
        event.widget.destroy()
        self.__currentInputColumn = None

        descLabel = tk.Label(
            parent, text=task.desc, anchor='w', **TaskListViewer.SELECTED_TASK_WIDGET_VIEW)
        descLabel.grid(
            row=0, column=column_properties.index, sticky='ew')
        descLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
        descLabel.bind('<Button-1>', self._onTaskSingleClick)

        self.__widgetMap[descLabel] = task.uid
        task_entry.descLabel = descLabel
        self.draw()
        self.__model.save()

    def markComplete(self, event: tk.Event = None):
        self.__log.debug("markComplete")
        task_entry = self.__activeTaskEntry
        if task_entry is None:
            raise RuntimeError
        self.__model.completeTask(task_entry.task)
        self.draw()
        self.__model.save()

    def getViewDefs(self, dueDate):
        self.__log.debug("getViewDefs")
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

    @dataclass
    class TaskEntry:
        task: Task
        frame: tk.Frame
        dateLabel: tk.Label
        projectLabel: Union[tk.Label, SelectableComboBox]
        actionLabel: Union[tk.Label, SelectableComboBox]
        descLabel: Union[tk.Label, tk.Entry]
        recurLabel: tk.Label
        row: int

    def _drawTasks(self):
        self.__log.debug("_drawTasks")
        if len(self.__taskMap) > 0:
            # clear existing
            for frame in [t.frame for t in self.__taskMap.values()]:
                frame.destroy()
        self.__taskMap.clear()
        self.__widgetMap.clear()
        self.__activeTaskEntry = None
        self.__currentInputColumn = None

        row = 1
        prog = re.compile(self.__filterPattern)
        for task in sorted(self.__model.getTasks()):
            project = task.project
            if not isinstance(project, Project):
                raise RuntimeError
            result = prog.match(project.name)
            if result is None:
                continue

            dueDate = task.dueDate
            frameView, widgetView = self.getViewDefs(dueDate)
            taskFrame = tk.Frame(self.__frame)
            taskFrame.configure(**frameView)
            taskFrame.grid(row=row, column=0, sticky='ew')
            for column in TaskListViewer.ColumnProperties.values():
                taskFrame.grid_columnconfigure(
                    column.index, minsize=column.width, weight=column.weight)

            datelabel = self.createDateLabel2(task, widgetView, taskFrame)

            projectLabel = tk.Label(
                taskFrame, text=project.name, anchor='w', **widgetView)
            projectLabel.grid(
                row=0, column=TaskListViewer.ColumnProperties[self.PROJECT].index, sticky='ew')
            projectLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
            projectLabel.bind('<Button-1>', self._onTaskSingleClick)

            actionLabel = tk.Label(
                taskFrame, text=Task.ActionStringMap[task.action], anchor='w', **widgetView)
            actionLabel.grid(
                row=0, column=TaskListViewer.ColumnProperties[self.ACTION].index, sticky='ew')
            actionLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
            actionLabel.bind('<Button-1>', self._onTaskSingleClick)

            descLabel = tk.Label(
                taskFrame, text=task.desc, anchor='w', **widgetView)
            descLabel.grid(
                row=0, column=TaskListViewer.ColumnProperties[self.DESCRIPTION].index, sticky='ew')
            descLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
            descLabel.bind('<Button-1>', self._onTaskSingleClick)

            if task.recurrence:
                recurText = u"\u2713"
            else:
                recurText = ' '
            recurLabel = tk.Label(
                taskFrame, text=recurText, anchor='w', **widgetView)
            recurLabel.grid(
                row=0, column=TaskListViewer.ColumnProperties[self.RECURRENCE].index, sticky='ew')
            recurLabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
            self.__taskMap[task.uid] = TaskListViewer.TaskEntry(
                task=task,
                frame=taskFrame,
                dateLabel=datelabel,
                projectLabel=projectLabel,
                actionLabel=actionLabel,
                descLabel=descLabel,
                recurLabel=recurLabel,
                row=row
            )
            project.registerOnChangeCallback(self.__doProjectChangeHandler, kwargs={'task_entry': self.__taskMap[task.uid]})
            self.__widgetMap[datelabel] = task.uid
            self.__widgetMap[projectLabel] = task.uid
            self.__widgetMap[actionLabel] = task.uid
            self.__widgetMap[descLabel] = task.uid
            self.__widgetMap[recurLabel] = task.uid
            row += 1

    def createDateLabel2(self, task: Task, widgetView: Dict[str, str], taskFrame: tk.Frame):
        datelabel = tk.Label(
            taskFrame, text=task.dueDate.strftime('%a, %b %d'), anchor='w', **widgetView)
        datelabel.grid(
            row=0, column=TaskListViewer.ColumnProperties[self.DATE].index, sticky='ew')
        datelabel.bind('<Double-Button-1>', self._onTaskDoubleClick)
        datelabel.bind('<Button-1>', self._onTaskSingleClick)
        return datelabel
