from __future__ import annotations

import logging
import threading
import time
from multiprocessing import AuthenticationError
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError
from uuid import UUID

import pyrebase
from pyrebase.pyrebase import Database, Firebase

from ProjectLog.data import Project, Task
from ProjectLog.serializable import Serializable


def initializeAppClient() -> Firebase:
    config = {
        "apiKey": "AIzaSyDwwHYGSdPllX9UjI28BPAtHP0YDkF8Jv8",
        "authDomain": "projectlog-e2824.firebaseapp.com",
        "databaseURL": "https://projectlog-e2824-default-rtdb.firebaseio.com",
        "storageBucket": "projectlog-e2824.appspot.com"
    }
    return pyrebase.initialize_app(config)

def initializeAppServer(creds: Path) -> Firebase:
    config = {
        "apiKey": "AIzaSyDwwHYGSdPllX9UjI28BPAtHP0YDkF8Jv8",
        "authDomain": "projectlog-e2824.firebaseapp.com",
        "databaseURL": "https://projectlog-e2824-default-rtdb.firebaseio.com",
        "storageBucket": "projectlog-e2824.appspot.com",
        'serviceAccount': creds.as_posix()
    }
    return pyrebase.initialize_app(config)


class TaskLog:
    config = {
        "apiKey": "AIzaSyDwwHYGSdPllX9UjI28BPAtHP0YDkF8Jv8",
        "authDomain": "projectlog-e2824.firebaseapp.com",
        "databaseURL": "https://projectlog-e2824-default-rtdb.firebaseio.com",
        "storageBucket": "projectlog-e2824.appspot.com"
    }

    def __init__(self) -> None:
        self.__firebase = pyrebase.initialize_app(self.config)
        self.__user: Optional[Dict[str, str]] = None
        self.__db: Optional[Database] = None
        self.__dataRoot: Optional[Path] = None
        self.__log = logging.getLogger('ProjectLog.TaskLog')
        self.__log.info('created')
        self.__token = ''
        self.__tasks: List[Task] = []
        self.__projects: List[Project] = []

    def authenticate(self, username: str, password: str) -> None:
        auth = self.__firebase.auth()
        try:
            self.__user = auth.sign_in_with_email_and_password(username, password)
            assert(isinstance(self.__user, dict))
            self.__token = self.__user['idToken']
            self.__db = self.__firebase.database()
            self.__dataRoot = Path('data', self.__user['localId'])
            self.__setUpDb()
            self.__loadFromDb()
            threading.Thread(target=self.__autoRefresh, daemon=True).start()

        except HTTPError:
            raise AuthenticationError

    def __loadFromDb(self):
        if self.__db is None or self.__dataRoot is None:
            raise RuntimeError
        objMap: Dict[UUID, Serializable] = {}
        response = self.__db.child(self.__dataRoot.as_posix()).get(token=self.__token)
        data = response.val()
        assert(isinstance(data, dict))
        if 'projects' in data:
            for id, project in data['projects'].items():
                project_object = Project.fromDict(project)
                objMap[project_object.uid] = project_object
                self.__projects.append(project_object)
                project_object.registerOnChangeCallback(self.__updateFirebaseProject)
        if 'tasks' in data:
            for id, task_data in data['tasks'].items():
                task_obj = Task.fromDict(task_data)
                objMap[task_obj.uid] = task_obj
                self.__tasks.append(task_obj)
                task_obj.registerOnChangeCallback(self.__updateFirebaseTask)
        
        # Resolve object references
        for project in self.__projects:
            project.complete(objMap)
        for task in self.__tasks:
            task.complete(objMap)
        return

    def __updateFirebaseTask(self, task: Task):
        if self.__dataRoot is None or self.__db is None:
            raise RuntimeError
        data = {
            self.__dataRoot.joinpath('tasks', task.uid.hex).as_posix(): task.toDict()
        }
        self.__db.update(data, token=self.__token)

    def __updateFirebaseProject(self, project: Project):
        if self.__dataRoot is None or self.__db is None:
            raise RuntimeError
        data = {
            self.__dataRoot.joinpath('projects', project.uid.hex).as_posix(): project.toDict()
        }
        self.__db.update(data, token=self.__token)
        
    def __setUpDb(self):
        if self.__dataRoot is None or self.__db is None:
            raise RuntimeError
        self.__db.update({
            self.__dataRoot.joinpath('initialized').as_posix(): True
        }, token=self.__token)

    def refreshAuth(self):
        if self.__user is None:
            raise RuntimeError
        auth = self.__firebase.auth()
        auth.refresh(self.__user['refreshToken'])

    def __autoRefresh(self):
        while(1):
            time.sleep(1800)
            self.refreshAuth()

    class AuthenticationError(RuntimeError):
        pass

    def addProject(self, project: Project):
        if self.__db is None or self.__dataRoot is None:
            raise RuntimeError
        self.__projects.append(project)
        data = {
            self.__dataRoot.joinpath('projects', project.uid.hex).as_posix(): project.toDict()
        }
        self.__db.update(data, token=self.__token)

    def addTask(self, task: Task):
        if self.__db is None or self.__dataRoot is None:
            raise RuntimeError
        self.__tasks.append(task)
        data = {
            self.__dataRoot.joinpath('tasks', task.uid.hex).as_posix():task.toDict()
        }
        self.__db.update(data, token=self.__token)

    def removeTask(self, task: Task):
        if task.recurrence:
            newDate = task.recurrence.getNextDate()
            task.dueDate = newDate

    def getTasks(self) -> List[Task]:
        return self.__tasks

    def getProjects(self) -> List[Project]:
        return self.__projects

    def close(self):
        pass

    def save(self):
        pass

    def completeTask(self, task: Task):
        if self.__db is None or self.__dataRoot is None:
            raise RuntimeError
        if task.recurrence:
            task.dueDate = task.recurrence.getNextDate()
        else:
            self.__tasks.remove(task)
            data = {
                self.__dataRoot.joinpath('tasks', task.uid.hex).as_posix():None,
                self.__dataRoot.joinpath('archivetasks', task.uid.hex).as_posix():task.toDict()
            }
            self.__db.update(data, token=self.__token)
