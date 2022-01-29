from pathlib import Path
from typing import List
from ProjectLog.config import Config
from ProjectLog.data import Project, Task, TaskList


class ProjectLogCore:
    def __init__(self):
        dataPath = Config.instance().dataPath
        dataPath.parent.mkdir(parents=True, exist_ok=True)
        self.__taskList = TaskList(Path('test.xml'))

    def close(self):
        self.__taskList.close()

    def getProjects(self) -> List[Project]:
        return self.__taskList.getProjects()

    def save(self) -> None:
        self.__taskList.save()
    
    def getProjectByName(self, name: str) -> Project:
        project = self.__taskList.getProjectByName(name)
        if project is None:
            raise ProjectLogCore.UnknownProjectError
        return project

    class UnknownProjectError(RuntimeError):
        pass

    def completeTask(self, task: Task) -> None:
        self.__taskList.removeTask(task)

    def getTasks(self) -> List[Task]:
        return self.__taskList.getTasks()