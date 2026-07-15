from ..template_manager import import_template
from .alignment import Alignment


class Fitting:

    def __init__(self, session):

        self.session = session

    def execute(self):

        print("\n========== FITTING ==========")

        self.session.template = import_template()

        print("Template imported successfully.")

        alignment = Alignment(self.session)
        alignment.execute()

