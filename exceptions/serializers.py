class ActionProhibited(Exception):
    def __init__(self, cls, action: str):
        self.cls = cls
        self.action = action

    def __str__(self):
        return f"{self.action} is prohibited for {self.cls.__name__}"

    def __repr__(self):
        return f"{self.action}Prohibited({self.cls.__name__})"
