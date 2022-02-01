
from __future__ import annotations

import datetime as dt
import logging
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Tuple, Union, Any, Optional
from uuid import UUID, uuid1

import schema

from ProjectLog.callbacks import Callback
from ProjectLog.serializable import Serializable


class Project(Serializable):

    def __init__(self, name: str, priority: Union[int, dt.date], tasks: List[Union[UUID, Task]] = None, uid: UUID = None) -> None:
        self.__name = name
        self.__priority = priority
        self.__tasks = tasks or []
        self.__uid = uid or uuid1()

        self.__changeCb: List[Callback] = []

    @property
    def tasks(self) -> List[Union[Task, UUID]]:
        return self.__tasks
    
    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, name: str):
        self.__name = name
        self.__doChangeCbs()

    @property
    def priority(self) -> Union[int, dt.date]:
        return self.__priority

    @priority.setter
    def priority(self, priority: Union[int, dt.date]):
        self.__priority = priority
        self.__doChangeCbs()

    @property
    def uid(self) -> UUID:
        return self.__uid


    def registerOnChangeCallback(self, fn: Callable, args: Tuple = (), kwargs: Dict[str, Any] = {}):
        self.__changeCb.append(Callback(fn=fn, kwargs=kwargs, args=args))

    def __doChangeCbs(self):
        for cb in self.__changeCb:
            cb.fn(*cb.args, **cb.kwargs, project=self)

    def addTask(self, task: Task):
        self.__tasks.append(task)

    def __eq__(self, other) -> bool:
        return self.name == other.name and self.priority == other.priority

    def __lt__(self, other):
        if isinstance(self.__priority, dt.date) and isinstance(other.priority, dt.date):
            if self.__priority < other.priority:
                return True
            elif self.__priority > other.priority:
                return False
            else:
                return self.__name < other.name
        elif isinstance(self.__priority, int) and isinstance(other.priority, int):
            if self.__priority < other.priority:
                return True
            elif self.__priority > other.priority:
                return False
            else:
                return self.__name < other.name
        elif isinstance(self.__priority, int) and isinstance(other.priority, dt.date):
            return False
        else:
            return True

    def removeTask(self, task: Task):
        self.__tasks.remove(task)

    def hasTasks(self):
        return len(self.__tasks) > 0

    def toDict(self) -> Dict[str, Union[str, int, List[str]]]:
        if isinstance(self.__priority, int):
            priority = self.__priority
        elif isinstance(self.__priority, dt.date):
            priority = self.__priority.toordinal()
        else:
            raise RuntimeError

        tasks = [task.uid.hex for task in self.__tasks if isinstance(task, Task)]
        tasks.extend([id.hex for id in self.__tasks if isinstance(id, UUID)])
        return {
            'name': self.__name,
            'priority': priority,
            'uid': self.__uid.hex
        }

    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> Project:
        projectSchema = schema.Schema(
            {
                'name': str,
                'priority': int,
                'uid': str
            }
        )
        projectSchema.validate(data)
        priority_value = data['priority']
        priority = cls.extract_priority_int(priority_value)
        tasks = []
        return Project(
            name=data['name'],
            priority=priority,
            tasks = tasks,
            uid=UUID(data['uid']))

    @classmethod
    def extract_priority_int(cls, priority_value: int):
        if priority_value < dt.date(2000, 1, 1).toordinal():
            priority = priority_value
        else:
            priority = dt.date.fromordinal(priority_value)
        return priority
    
    def isComplete(self) -> bool:
        return all([isinstance(t, Task) for t in self.tasks])

    def complete(self, objects: Dict[UUID, Serializable]):
        for t in [t for t in self.tasks if isinstance(t, UUID)]:
            obj = self._resolveObj(t, Task, objects)
            if obj is not None:
                self.__tasks.append(obj)
                self.__tasks.remove(t)


class Recurrence(Serializable):

    def __init__(self, recurrence: str, value: int, dueDate: dt.date) -> None:
        self.__recurrence = recurrence
        self.__value = value
        self.__dueDate = dueDate
        self.__changeCb: List[Callback] = []

    @property
    def dueDate(self) -> dt.date:
        return self.__dueDate

    @dueDate.setter
    def dueDate(self, dueDate: dt.date):
        self.__dueDate = dueDate
        self.__doChangeCbs()

    @property
    def value(self) -> int:
        return self.__value

    @value.setter
    def value(self, value: int):
        self.__value = value
        self.__doChangeCbs()

    @property
    def recurrence(self) -> str:
        return self.__recurrence

    @recurrence.setter
    def recurrence(self, recurrence: str):
        self.__recurrence = recurrence
        self.__doChangeCbs()

    def registerOnChangeCallback(self, fn: Callable, args: Tuple = (), kwargs: Dict[str, Any] = {}):
        self.__changeCb.append(Callback(fn=fn, kwargs=kwargs, args=args))

    def __doChangeCbs(self):
        for cb in self.__changeCb:
            cb.fn(*cb.args, **cb.kwargs, task=self)    

    DAILY_RECURRENCE = "daily"
    WEEKDAY_RECURRENCE = "weekday"
    MONTHDAY_RECURRENCE = "monthday"
    MONTHWEEKDAY_RECURRENCE = "monthwday"
    options = (DAILY_RECURRENCE, WEEKDAY_RECURRENCE,
               MONTHDAY_RECURRENCE, MONTHWEEKDAY_RECURRENCE)

    def getNextDate(self) -> dt.date:
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
        else:
            raise RuntimeError
    
    def toDict(self) -> Dict[str, Any]:
        return {
            'recurrence': self.recurrence,
            'value': self.value,
            'dueDate': self.dueDate.toordinal()
        }

    recurrenceSchema = schema.Schema(
        {
            'recurrence': lambda x: x in [Recurrence.DAILY_RECURRENCE, Recurrence.WEEKDAY_RECURRENCE, Recurrence.MONTHDAY_RECURRENCE, Recurrence.MONTHWEEKDAY_RECURRENCE],
            'value': int,
            'dueDate': int
        }
    )
    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> Recurrence:

        cls.recurrenceSchema.validate(data)

        return Recurrence(
            recurrence=data['recurrence'],
            value=data['value'],
            dueDate=dt.date.fromordinal(data['dueDate'])
        )

    def isComplete(self) -> bool:
        return True
    
    def complete(self, objects: Dict[UUID, Serializable]):
        return super().complete(objects)

class Task(Serializable):

    def __init__(self, dueDate: dt.date, project: Union[Project, UUID], desc: str, action: Action, recurrence: Optional[Recurrence] = None, uid: UUID = None) -> None:
        self.__dueDate = dueDate
        self.__project = project
        self.__desc = desc
        self.__action = action
        self.__recurrence = recurrence
        if uid is None:
            self.__uid = uuid1()
        else:
            self.__uid = uid

        self.__changeCb: List[Callback] = []
        if isinstance(self.__project, Project):
            self.__project.addTask(self)

    def registerOnChangeCallback(self, fn: Callable, args: Tuple = (), kwargs: Dict[str, Any] = {}):
        self.__changeCb.append(Callback(fn=fn, kwargs=kwargs, args=args))

    def __doChangeCbs(self):
        for cb in self.__changeCb:
            cb.fn(*cb.args, **cb.kwargs, task=self)

    @property
    def uid(self) -> UUID:
        return self.__uid

    @property
    def recurrence(self) -> Optional[Recurrence]:
        return self.__recurrence

    @recurrence.setter
    def recurrence(self, recurrence: Optional[Recurrence]):
        self.__recurrence = recurrence
        self.__doChangeCbs()

    @property
    def action(self) -> Action:
        return self.__action

    @action.setter
    def action(self, action: Action):
        self.__action = action
        self.__doChangeCbs()

    @property
    def desc(self) -> str:
        return self.__desc

    @desc.setter
    def desc(self, desc: str):
        self.__desc = desc
        self.__doChangeCbs()

    @property
    def project(self) -> Union[Project, UUID]:
        return self.__project

    @project.setter
    def project(self, project: Union[Project, UUID]):
        self.__project = project
        self.__doChangeCbs()

    @property
    def dueDate(self) -> dt.date:
        return self.__dueDate
    
    @dueDate.setter
    def dueDate(self, dueDate: dt.date):
        self.__dueDate = dueDate
        self.__doChangeCbs()

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

    def __eq__(self, other):
        return self is other

    def __lt__(self, other):
        if self.__dueDate < other.dueDate:
            return True
        elif self.__dueDate > other.dueDate:
            return False
        else:
            if self.__project < other.project:
                return True
            elif self.__project > other.project:
                return False
            else:
                if self.__action.value < other.action.value:
                    return True
                elif self.__action.value > other.action.value:
                    return False
                else:
                    return self.__desc < other.desc

    def complete(self, objects: Dict[UUID, Serializable]):
        if isinstance(self.project, UUID):
            obj = self._resolveObj(self.project, Project, objects)
            if obj is not None:
                self.__project = obj
                self.__project.addTask(self)
            
    
    def isComplete(self) -> bool:
        return isinstance(self.__project, UUID)

    def toDict(self) -> Dict[str, Any]:
        if isinstance(self.__project, Project):
            project = self.__project.uid.hex
        elif isinstance(self.__project, UUID):
            project = self.__project.hex
        else:
            raise RuntimeError
        data = {
            'dueDate': self.__dueDate.toordinal(),
            'project': project,
            'desc': self.__desc,
            'action': self.__action.value,
            'uid': self.__uid.hex
        }

        if self.__recurrence is not None:
            data['recurrence'] = self.__recurrence.toDict()
        return data

    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> Task:
        taskSchema = schema.Schema(
            {
                'dueDate': int,
                'project': str,
                'desc': str,
                'action': int,
                'uid': str,
                schema.Optional('recurrence'): Recurrence.recurrenceSchema
            }
        )

        taskSchema.validate(data)
        if 'recurrence' in data:
            recurrence = Recurrence.fromDict(data['recurrence'])
        else:
            recurrence = None
        
        return Task(
            dueDate=dt.date.fromordinal(data['dueDate']),
            project=UUID(data['project']),
            desc=data['desc'],
            action=cls.Action(data['action']),
            uid=UUID(data['uid']),
            recurrence=recurrence
        )
