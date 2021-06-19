'''
Created on Dec 20, 2020

@author: ntlhui
'''

from enum import Enum
import datetime as dt
import uuid
import logging
import xml.etree.ElementTree as ET
import os

ENABLE_BACKUP_XML = True


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


class Recurrence:

    DAILY_RECURRENCE = "daily"
#     DAY_RECURRENCE = "day"
#     WEEKLY_RECURRENCE = "weekly"
    WEEKDAY_RECURRENCE = "weekday"
#     MONTHLY_RECURRENCE = "monthly"
    MONTHDAY_RECURRENCE = "monthday"
    MONTHWEEKDAY_RECURRENCE = "monthwday"
#     YEARLY_RECURRENCE = "yearly"
    options = (DAILY_RECURRENCE, WEEKDAY_RECURRENCE,
               MONTHDAY_RECURRENCE, MONTHWEEKDAY_RECURRENCE)

    def __init__(self, recurrenceType: str, value: int, startDate: dt.date = None):
        '''

        :param type:
        :type type:
        '''
        if startDate is None:
            startDate = dt.date.today()

        self.recurrence = recurrenceType
        self.value = value
        self.dueDate = startDate

        pass

    def getNextDate(self):
        if self.recurrence == self.DAILY_RECURRENCE:
            return self.dueDate + dt.timedelta(days=self.value)
        elif self.recurrence == self.WEEKDAY_RECURRENCE:
            return self.dueDate + dt.timedelta(days=7 * self.value)
        elif self.recurrence == self.MONTHDAY_RECURRENCE:
            dayOfMonth = self.dueDate.day
            year = self.dueDate.year
            month = self.dueDate.month + self.value
            return dt.date(year, month, dayOfMonth)
        elif self.recurrence == self.MONTHWEEKDAY_RECURRENCE:
            weekday = self.dueDate.weekday()
            weekNum = int(self.dueDate.day - 1 / 7) + 1
            nextMonth = (self.dueDate.replace(day=1) +
                         dt.timedelta(days=32)).replace(day=1)
            adj = nextMonth.weekday() - weekday
            nextMonth += dt.timedelta(days=adj)
            nextMonth += dt.timedelta(weeks=weekNum)
            return nextMonth

    def setDueDate(self, date: dt.date):
        self.dueDate = date


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
                 desc: str, action: Action = Action.DO, uid=None, recurrence=None):
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
        self.recurrence = recurrence

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
        if self.recurrence:
            self.recurrence.setDueDate(date)

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

    def setRecurrence(self, recurrence: Recurrence):
        self.recurrence = recurrence

    def getRecurrence(self):
        return self.recurrence


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

            # optionals
            taskRecurrence = None
            for optional in task.getchildren():
                if optional.tag == 'recurrence':
                    taskRecurrence = Recurrence(optional.attrib['type'], int(
                        optional.attrib['value']), dt.datetime.strptime(optional.attrib['date'], '%m/%d/%y').date())

            taskObj = Task(taskDate, project, taskDesc,
                           taskAction, taskID, recurrence=taskRecurrence)
            self._tasks.append(taskObj)

        return self

    def open(self):
        self.__enter__()

    def close(self):
        self.__exit__(None, None, None)

    def save(self, *args):
        if ENABLE_BACKUP_XML:
            os.rename(self.__fname, "test_%s.xml" %
                      (dt.datetime.now().strftime("%Y.%m.%d.%H.%M.%S")))

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

            # optionals
            if task.getRecurrence():
                recurrenceElement = ET.SubElement(taskElement, 'recurrence')
                recurrenceElement.set('type', task.getRecurrence().recurrence)
                recurrenceElement.set('value', str(task.getRecurrence().value))
                recurrenceElement.set(
                    'date', task.getRecurrence().dueDate.strftime('%m/%d/%y'))

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
            raise RuntimeError("Project still has active tasks")
        self.__projects.remove(project)

    def removeTask(self, task: Task):
        if task.getRecurrence():
            newDate = task.getRecurrence().getNextDate()
            task.setDate(newDate)
        else:
            self._tasks.remove(task)
            task.getProject().removeTask(task)
