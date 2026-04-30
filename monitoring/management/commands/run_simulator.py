import time
from django.core.management.base import BaseCommand
from monitoring.simulation_writers import write_industry_reading, write_stp_reading


class Command(BaseCommand):
    help = "Runs effluent simulation"

    def handle(self, *args, **kwargs):

        print("Simulator started...")

        while True:
            write_industry_reading("IND_A")
            write_industry_reading("IND_B")
            write_industry_reading("IND_C")
            write_stp_reading("STP_1")

            time.sleep(10)
