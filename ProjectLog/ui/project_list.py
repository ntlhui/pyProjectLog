from __future__ import annotations

import datetime as dt
import tkinter as tk
import tkinter.messagebox as tkm
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Union
from uuid import UUID

import tkcalendar as tkc
from ProjectLog.firebase import Project, TaskLog
from ProjectLog.ui.theme import ThemeManager


class ProjectListviewer(tk.Frame):

    class Columns(Enum):
        NAME = {'index': 1, 'width': 120, 'label': 'Project', 'weight': 1}
        DATE = {'index': 0, 'width': 85, 'label': 'Date', 'weight': 0}

    SELECTED_PROJECT_FRAME_VIEW = {
        "highlightbackground": 'black', 'highlightthickness': 1}
    SELECTED_PROJECT_WIDGET_VIEW = {'bg': ThemeManager.SELECTION_COLOR}
    NORMAL_PROJECT_FRAME_VIEW = {
        'highlightbackground': 'black', 'highlightthickness': 1}
    NORMAL_PROJECT_WIDGET_VIEW = {'bg': ThemeManager.BACKGROUND_COLOR}

    def __init__(self, parent, model: TaskLog):
        super().__init__(parent)
        self.__model = model
        self.__dataFrame = None
        self.__inputVar = tk.StringVar()
        self.__projectMap: Dict[UUID, ProjectListviewer.ProjectEntries] = {}
        self.__widgetMap: Dict[tk.Widget, UUID] = {}
        self.__active_project_entry: Optional[ProjectListviewer.ProjectEntries] = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.draw()

    @dataclass
    class ProjectEntries:
        project: Project
        frame: tk.Frame
        nameWidget: tk.Widget
        priorityWidget: tk.Widget
        row: int

        @property
        def widgets(self) -> List[tk.Widget]:
            return [self.nameWidget, self.priorityWidget]

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

        self.__projectMap.clear()
        self.__widgetMap.clear()
        self.__active_project_entry = None

        self.__currentInputType = None
        self.__currentInputWidget = None

        for project in sorted(self.__model.getProjects()):
            projectFrame = tk.Frame(
                self.__dataFrame, **ProjectListviewer.NORMAL_PROJECT_FRAME_VIEW)
            projectFrame.grid(row=row, column=0, sticky='ew')
            for column in ProjectListviewer.Columns:
                projectFrame.grid_columnconfigure(
                    column.value['index'], minsize=column.value['width'], weight=column.value['weight'])

            nameLabel = tk.Label(projectFrame, text=project.name, anchor='w')
            nameLabel.grid(
                row=0, column=ProjectListviewer.Columns.NAME.value['index'], sticky='ew')
            nameLabel.bind('<Double-Button-1>', self._onProjectDoubleClick)
            nameLabel.bind('<Button-1>', self._onProjectSingleClick)

            project_priority = project.priority
            dateLabel = self.createPriorityLabel(0, projectFrame, project_priority)

            self.__projectMap[project.uid] = ProjectListviewer.ProjectEntries(
                project=project,
                frame=projectFrame,
                nameWidget=nameLabel,
                priorityWidget=dateLabel,
                row=0
            )
            self.__widgetMap[nameLabel] = project.uid
            self.__widgetMap[dateLabel] = project.uid
            row += 1
        self.__dataFrame.grid(row=0, column=0)

    def createPriorityLabel(self, row:int, projectFrame:tk.Frame, project_priority: Union[dt.date, int]):
        if isinstance(project_priority, dt.date):
            dateText = project_priority.strftime('%m/%d/%Y')
        else:
            dateText = f'{project_priority}'
        dateLabel = tk.Label(projectFrame, text=dateText, anchor='w')
        dateLabel.grid(
                row=row, column=ProjectListviewer.Columns.DATE.value['index'], sticky='ew')
        dateLabel.bind('<Double-Button-1>', self._onProjectDoubleClick)
        dateLabel.bind('<Button-1>', self._onProjectSingleClick)
        return dateLabel

    def _onProjectDoubleClick(self, event: tk.Event):
        project_id = self.__widgetMap[event.widget]
        project_entry = self.__projectMap[project_id]
        project = project_entry.project
        frame = project_entry.frame
        

        if self.__active_project_entry is None:
            # select from nothing else
            frame.configure(**ProjectListviewer.SELECTED_PROJECT_FRAME_VIEW)
            for widget in project_entry.widgets:
                widget.configure(
                    **ProjectListviewer.SELECTED_PROJECT_WIDGET_VIEW)
            self.__active_project_entry = project_entry
        else:
            self.__active_project_entry.frame.configure(
                **ProjectListviewer.NORMAL_PROJECT_FRAME_VIEW)
            for widget in self.__active_project_entry.widgets:
                widget.configure(
                    **ProjectListviewer.NORMAL_PROJECT_WIDGET_VIEW)

            frame.configure(**ProjectListviewer.SELECTED_PROJECT_FRAME_VIEW)
            for widget in project_entry.widgets:
                widget.configure(
                    **ProjectListviewer.SELECTED_PROJECT_WIDGET_VIEW)

            self.__active_project_entry = project_entry

        # set current widget to edit mode
        self.__widgetMap.pop(event.widget)
        event.widget.destroy()

        if event.widget is project_entry.nameWidget:
            # name widget
            self.__inputVar.set(project.name)

            descEntry = tk.Entry(frame, textvariable=self.__inputVar)
            descEntry.grid(
                row=0, column=ProjectListviewer.Columns.NAME.value['index'], sticky='ew')
            descEntry.bind('<Return>', self._onNameEntered)
            descEntry.bind('<KP_Enter>', self._onNameEntered)
            descEntry.focus_set()

            project_entry.nameWidget = descEntry
            self.__currentInputWidget = descEntry
            self.__currentInputType = ProjectListviewer.Columns.NAME
            self.__widgetMap[descEntry] = project.uid
        else:
            # date widget
            priority = project.priority
            input_variable = self.__inputVar
            callback = self._onPriorityEntered
            dateEntry = self.createDateEntry(frame, priority, input_variable, callback)

            project_entry.priorityWidget = dateEntry
            self.__currentInputWidget = dateEntry
            self.__currentInputType = ProjectListviewer.Columns.DATE
            self.__widgetMap[dateEntry] = project.uid

    def createDateEntry(self, frame, priority, input_variable, callback):
        if isinstance(priority, dt.date):
            dateEntry = tkc.DateEntry(
                    master=frame,
                    textvariable=input_variable,
                    firstweekday='sunday',
                    year=priority.year,
                    month=priority.month,
                    day=priority.day)
            dateEntry.bind('<<DateEntrySelected>>', callback)
        elif isinstance(priority, int):
            input_variable.set(f'{priority}')
            dateEntry = tk.Entry(frame, textvariable=input_variable)
            dateEntry.bind('<Return>', callback)
            dateEntry.bind('<KP_Enter>', callback)
        else:
            raise RuntimeError
        dateEntry.grid(
                row=0,
                column=ProjectListviewer.Columns.DATE.value['index'],
                sticky='ew')
            
        return dateEntry

    def _onProjectSingleClick(self, event):
        project_id = self.__widgetMap[event.widget]
        project_entry = self.__projectMap[project_id]
        project = project_entry.project
        active_project_entry = self.__active_project_entry

        if active_project_entry is not None:
            # cancel current input
            if self.__currentInputType == ProjectListviewer.Columns.DATE:
                parent = self.__currentInputWidget.master
                self.__widgetMap.pop(self.__currentInputWidget)
                self.__currentInputWidget.grid_remove()
                self.__currentInputType = None
                self.__currentInputWidget = None

                project_priority = active_project_entry.project.priority
                if isinstance(project_priority, dt.date):
                    priority_text = project_priority.strftime('%m/%d/%Y')
                else:
                    priority_text = project_priority

                dateLabel = tk.Label(parent, text=priority_text, anchor='w', **ProjectListviewer.NORMAL_PROJECT_WIDGET_VIEW)
                dateLabel.grid(
                    row=0, column=ProjectListviewer.Columns.DATE.value['index'], sticky='ew')
                dateLabel.bind('<Double-Button-1>', self._onProjectDoubleClick)
                dateLabel.bind('<Button-1>', self._onProjectSingleClick)

                self.__widgetMap[dateLabel] = active_project_entry.project.uid
                active_project_entry.priorityWidget = dateLabel
            elif self.__currentInputType == ProjectListviewer.Columns.NAME:
                parent = self.__currentInputWidget.master
                self.__widgetMap.pop(self.__currentInputWidget)
                self.__currentInputWidget.grid_remove()
                self.__currentInputType = None
                self.__currentInputWidget = None

                descLabel = tk.Label(parent, text=self.__active_project_entry.getName(
                ), anchor='w', **ProjectListviewer.NORMAL_PROJECT_WIDGET_VIEW)
                descLabel.grid(
                    row=0, column=ProjectListviewer.Columns.NAME.value['index'], sticky='ew')
                descLabel.bind('<Double-Button-1>', self._onProjectDoubleClick)
                descLabel.bind('<Button-1>', self._onProjectSingleClick)

                self.__widgetMap[descLabel] = self.__active_project_entry.project.uid
                self.__active_project_entry.nameWidget = descLabel

        # Toggle current project
        frame = project_entry.frame
        widgets = project_entry.widgets
        if project is self.__active_project_entry:
            # deselect current project
            frame.configure(**ProjectListviewer.NORMAL_PROJECT_FRAME_VIEW)
            for widget in widgets:
                widget.configure(
                    **ProjectListviewer.NORMAL_PROJECT_WIDGET_VIEW)
            self.__active_project_entry = None
        elif self.__active_project_entry is None:
            # select from nothing else
            frame.configure(**ProjectListviewer.SELECTED_PROJECT_FRAME_VIEW)
            for widget in widgets:
                widget.configure(
                    **ProjectListviewer.SELECTED_PROJECT_WIDGET_VIEW)
            self.__active_project_entry = project_entry
        else:
            self.__active_project_entry.frame.configure(
                **ProjectListviewer.NORMAL_PROJECT_FRAME_VIEW)
            for widget in self.__active_project_entry.widgets:
                widget.configure(
                    **ProjectListviewer.NORMAL_PROJECT_WIDGET_VIEW)

            frame.configure(**ProjectListviewer.SELECTED_PROJECT_FRAME_VIEW)
            for widget in widgets:
                widget.configure(
                    **ProjectListviewer.SELECTED_PROJECT_WIDGET_VIEW)
            self.__active_project_entry = project_entry

    def _onNameEntered(self, event: tk.Event):
        project_id = self.__widgetMap[event.widget]
        project_entry = self.__projectMap[project_id]
        project = project_entry.project

        name = self.__inputVar.get()
        project.name = name

        parent = project_entry.frame
        self.__widgetMap.pop(event.widget)
        event.widget.destroy()
        self.__currentInputType = None
        self.__currentInputWidget = None

        descLabel = tk.Label(parent, text=project.name, anchor='w', **ProjectListviewer.SELECTED_PROJECT_WIDGET_VIEW)
        descLabel.grid(
            row=0, column=ProjectListviewer.Columns.NAME.value['index'], sticky='ew')
        descLabel.bind('<Double-Button-1>', self._onProjectDoubleClick)
        descLabel.bind('<Button-1>', self._onProjectSingleClick)
        

        self.__widgetMap[descLabel] = project.uid
        project_entry.nameWidget = descLabel
        self.draw()
        self.__model.save()

    def _onPriorityEntered(self, event:tk.Event):
        # Update date
        project_id = self.__widgetMap[event.widget]
        project_entry = self.__projectMap[project_id]
        project = project_entry.project

        parent = project_entry.frame
        self.__widgetMap.pop(event.widget)
        event.widget.destroy()
        self.__currentInputType = None
        self.__currentInputWidget = None

        if isinstance(event.widget, tkc.DateEntry):
            project.priority = dt.datetime.strptime(self.__inputVar.get(), '%m/%d/%y').date()
            if project.priority < dt.date(2000, 1, 1):
                project.priority = project.priority.toordinal()
        elif isinstance(event.widget, tk.Entry):
            project.priority = Project.extract_priority_int(int(self.__inputVar.get()))
        
        dateLabel = self.createPriorityLabel(0, parent, project.priority)

        self.__widgetMap[dateLabel] = project.uid
        project_entry.priorityWidget = dateLabel
        self.draw()
        self.__model.save()

    def removeProject(self):
        if self.__active_project_entry is None:
            return
        try:
            self.__model.removeProject(self.__active_project_entry)
        except RuntimeError as e:
            tkm.showerror(title='Error', message=str(e))
        self.draw()
        self.__model.save()
