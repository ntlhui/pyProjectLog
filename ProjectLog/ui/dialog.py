import datetime as dt
import logging
import tkinter as tk
from tkinter import ttk
from typing import Any, Optional

import tkcalendar as tkc
from ProjectLog.data import Project, Recurrence, Task
from ProjectLog.firebase import TaskLog
from ProjectLog.ui.widgets import SelectableComboBox

class RecurrenceDialog(tk.Toplevel):
    def __init__(self, parent, recurrence: Recurrence = None, dueDate: dt.date = None):
        self.__parent = parent
        self.recurrence = recurrence

        if self.recurrence:
            self.__typeSelector = tk.StringVar(
                value=self.recurrence.recurrence)
            self.__valueSelector = tk.IntVar(value=self.recurrence.value)
            self.__dateSelector = tk.StringVar(
                value=self.recurrence.dueDate.strftime("%m/%d/%y"))
            self.__initialDate = self.recurrence.dueDate
        else:
            self.__typeSelector = tk.StringVar(
                value=Recurrence.DAILY_RECURRENCE)
            self.__valueSelector = tk.IntVar(value=1)
            self.__dateSelector = tk.StringVar(
                value=dueDate.strftime("%m/%d/%y"))
            self.__initialDate = dueDate

        self.__bodyFrame = None

        tk.Toplevel.__init__(self, parent)

        self.transient(parent)
        self.title("Recurrence")
        self.__createWidget()
        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50,
                                  parent.winfo_rooty() + 50))

        self.wait_window(self)

    def __createWidget(self):
        if self.__bodyFrame:
            self.__bodyFrame.destroy()

        self.__bodyFrame = tk.Frame(self)
        self.__bodyFrame.grid_columnconfigure(0, weight=1, pad=5)
        self.__bodyFrame.grid_columnconfigure(1, weight=1, pad=5)

        tk.Label(self.__bodyFrame, text='Recurrence Type').grid(
            row=0, column=0, sticky='ew')
        tk.Label(self.__bodyFrame, text='Recurrence Value').grid(
            row=1, column=0, sticky='ew')
        tk.Label(self.__bodyFrame, text='Recurrence Date').grid(
            row=2, column=0, sticky='ew')

        combobox = ttk.Combobox(
            self.__bodyFrame, textvariable=self.__typeSelector)
        combobox['values'] = Recurrence.options
        combobox.grid(row=0, column=1, sticky='ew')

        tk.Entry(self.__bodyFrame, textvariable=self.__valueSelector).grid(
            row=1, column=1, sticky='ew')

        tkc.DateEntry(
            self.__bodyFrame, textvariable=self.__dateSelector, firstweekday='sunday', year=self.__initialDate.year, month=self.__initialDate.month, day=self.__initialDate.day).grid(row=2, column=1, sticky='ew')

        tk.Button(self.__bodyFrame, text='OK',
                  command=self.__ok).grid(row=3, column=0)
        tk.Button(self.__bodyFrame, text='Cancel',
                  command=self.__cancel).grid(row=3, column=1)

        self.__bodyFrame.grid(row=0, column=0, sticky='ew')

    def __ok(self, event=None):
        self.withdraw()
        self.update_idletasks()
        if self.recurrence:
            self.recurrence.dueDate = dt.datetime.strptime(
                self.__dateSelector.get(), '%m/%d/%y').date()
            self.recurrence.recurrence = self.__typeSelector.get()
            self.recurrence.value = self.__valueSelector.get()
        else:
            self.recurrence = Recurrence(self.__typeSelector.get(), self.__valueSelector.get(), dt.datetime.strptime(
                self.__dateSelector.get(), '%m/%d/%y').date())
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


class AddTaskDialog(tk.Toplevel):
    def __init__(self, parent: Any, tasklist: TaskLog):
        self.__parent = parent
        self.__taskList = tasklist
        self.__bodyFrame: Optional[tk.Frame] = None
        self.__acceptFrame = None
        self.__initial_focus = None
        self.__dateSelector = tk.StringVar()
        self.__actionSelector = tk.Variable()
        self.__actionSelector.set(Task.ActionStringMap[Task.Action.DO])
        self.__projectSelector = tk.Variable()
        self.__descVar = tk.StringVar()
        self.__recurrence = None
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

        today = dt.datetime.today()
        tomorrow = (today + dt.timedelta(days=1)).date()

        dateEntry = tkc.DateEntry(self.__bodyFrame, textvariable=self.__dateSelector,
                                  mindate=dt.datetime.today().date(), firstweekday='sunday')
        dateEntry.set_date(tomorrow)
        dateEntry.grid(row=0, column=0, sticky='ew')

        project_options = {project.name: project for project in sorted(self.__taskList.getProjects())}
        self.projectMenu = SelectableComboBox(
            master=self.__bodyFrame,
            values=project_options,
            variable=self.__projectSelector,
            initial_value=''
        )
        self.projectMenu.configure(takefocus=1)
        self.projectMenu.grid(row=1, column=0, sticky='ew')

        action_options = {Task.ActionStringMap[action]:action for action in Task.Action}
        self.actionMenu = SelectableComboBox(
            master=self.__bodyFrame,
            values=action_options,
            initial_value='',
            variable=self.__actionSelector
        )
        self.actionMenu.configure(takefocus=1)
        self.actionMenu.grid(row=2, column=0, sticky='ew')

        descEntry = tk.Entry(self.__bodyFrame, textvariable=self.__descVar)
        descEntry.grid(row=3, column=0, sticky='ew')
        descEntry.bind('<Return>', self.__ok)
        descEntry.bind('<KP_Enter>', self.__ok)

        recurrenceButton = tk.Button(
            self.__bodyFrame, text="Recurrence", command=self.__recur)
        recurrenceButton.grid(row=4, column=0, sticky='ew')

        buttonFrame = tk.Frame(self.__bodyFrame)
        buttonFrame.grid_columnconfigure(0, weight=1)
        buttonFrame.grid_columnconfigure(1, weight=1)
        buttonFrame.grid(row=5, column=0, sticky='ew')

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
        project = self.projectMenu.currentValue
        desc = self.__descVar.get()
        action = self.actionMenu.currentValue

        task = Task(dueDate, project, desc, action,
                    recurrence=self.__recurrence)
        self.__taskList.addTask(task)
        self.__cancel()

    def __cancel(self, event=None):
        self.__parent.focus_set()
        self.destroy()

    def __recur(self, event=None):
        if self.__recurrence:
            dialog = RecurrenceDialog(self, self.__recurrence)
        else:
            print(self.__dateSelector.get())
            dialog = RecurrenceDialog(self, dueDate=dt.datetime.strptime(
                self.__dateSelector.get(), '%m/%d/%y').date())
            self.__recurrence = dialog.recurrence


