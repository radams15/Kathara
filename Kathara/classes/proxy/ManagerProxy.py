import utils
from ..foundation.manager.IManager import IManager
from ..setting.Setting import Setting


class ManagerProxy(IManager):
    __slots__ = ['manager']

    __instance = None

    @staticmethod
    def get_instance():
        if ManagerProxy.__instance is None:
            ManagerProxy()

        return ManagerProxy.__instance

    def __init__(self):
        if ManagerProxy.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            deployer_type = Setting.get_instance().deployer_type

            self.manager = utils.class_for_name("classes.manager.%s" % deployer_type,
                                                 "%sManager" % deployer_type.capitalize()
                                                )()

            ManagerProxy.__instance = self

    def deploy_lab(self, lab, options=None):
        self.manager.deploy_lab(lab, options)

    def undeploy_lab(self, lab_hash, selected_machines):
        self.manager.undeploy_lab(lab_hash, selected_machines)

    def wipe(self):
        self.manager.wipe()

    def connect_tty(self, lab_hash, machine_name, shell):
        self.manager.connect_tty(lab_hash, machine_name, shell)

    def get_lab_info(self, lab_hash=None):
        return self.manager.get_lab_info(lab_hash)

    def get_machine_info(self, machine_name):
        return self.manager.get_machine_info(machine_name)

    def get_version(self):
        return self.manager.get_version()
